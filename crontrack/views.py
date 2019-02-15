import logging
import re
from datetime import datetime
from itertools import chain

import pytz
from croniter import croniter, CroniterBadCronError  # see https://pypi.org/project/croniter/#usage

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.views.decorators.csrf import csrf_exempt

from .forms import ProfileForm, RegisterForm
from .models import Job, JobGroup, JobAlert, User, UserGroup, UserGroupMembership

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'crontrack/index.html')

def notify_job(request, id):
    job = Job.objects.get(pk=id)
    job.last_notified = timezone.now()
    job.save()
    logger.debug(f"Notified for job '{id}' at {job.last_notified}")
    
    return JsonResponse({'success_message': 'Job notified successfully.'})

@login_required
def view_jobs(request):
    timezone.activate(request.user.timezone)
    
    context = {
        'user_groups': [{'id': 'All', 'job_groups': [], 'empty': True}],
        'protocol': settings.SITE_PROTOCOL,
        'domain': settings.SITE_DOMAIN
    }
    for user_group in chain((None,), request.user.user_groups.all()):
        ungrouped = (get_job_group(request.user, None, user_group),)
        grouped = (get_job_group(request.user, g, user_group) for g in JobGroup.objects.all())
        
        if user_group is None:
            id = None
        else:
            id = user_group.id
        job_groups = [group for group in chain(ungrouped, grouped) if group is not None]
        empty = not any(group['jobs'] for group in job_groups)
        
        context['user_groups'].append({'id': id, 'job_groups': job_groups, 'empty': empty})
        context['user_groups'][0]['job_groups'] += job_groups
        context['user_groups'][0]['empty'] = empty and context['user_groups'][0]['empty']
    
    return render(request, 'crontrack/viewjobs.html', context)

@login_required
def add_job(request):
    if request.method == 'POST':
        context = {'prefill': request.POST}
        # Logic to add the job
        try:
            now = datetime.now(tz=pytz.timezone(request.POST['timezone']))
            
            # Determine which user group we're adding to
            if request.POST['user_group'] == 'None':
                user_group = None
            else:
                user_group = UserGroup.objects.get(pk=request.POST['user_group'])
                if user_group not in request.user.user_groups.all():
                    user_group = None
                    logger.warning(f"User {request.user} tried to access a group they\'re not in: {user_group}")
            
            # Check if we're adding a group
            if 'group' in request.POST:
                with transaction.atomic():
                    group = JobGroup(
                        user=request.user,
                        name=request.POST['name'],
                        description=request.POST['description'],
                        user_group=user_group,
                    )
                    group.full_clean()
                    logger.debug(f'Adding new group: {group}')
                    group.save()
                    
                    job_name = '[unnamed job]'
                    have_added_job = False
                    for line in request.POST['group_schedule'].split('\n'):
                        # Check if line is empty or starts with whitespace, and skip
                        if not line or line[0] in (' ', '\t', '\r'):
                            continue
                        # Interpret the line as a job name if it starts with '#'
                        if line[0] == '#':
                            job_name = line[1:].strip()
                            continue
                        
                        # Otherwise, process the line as a Cron schedule string
                        schedule_str = ' '.join(line.split(' ')[:5])
                        time_window = int(request.POST['time_window'])
                        if time_window < 0:
                            raise ValueError
                        job = Job(
                            user=request.user,
                            name=job_name,
                            schedule_str=schedule_str,
                            time_window=time_window,
                            next_run=croniter(schedule_str, now).get_next(datetime),
                            group=group,
                            user_group=user_group,
                        )
                        job.full_clean()
                        logger.debug(f'Adding new job: {job}')
                        have_added_job = True
                        job.save()
                    if not have_added_job:
                        # We didn't get any jobs
                        context['error_message'] = "no valid jobs entered"
                        return render(request, 'crontrack/addjob.html', context)
                    
                    # Group added successfully, open it up for editing
                    context = {'group': get_job_group(request.user, group, user_group)}
                    return render(request, 'crontrack/editgroup.html', context)
            
            # Otherwise, just add the single job
            else:
                time_window = int(request.POST['time_window'])
                if time_window < 0:
                    raise ValueError
                job = Job(
                    user=request.user,
                    name=request.POST['name'],
                    schedule_str=request.POST['schedule_str'],
                    time_window=time_window,
                    description=request.POST['description'],
                    next_run=croniter(request.POST['schedule_str'], now).get_next(datetime),
                    user_group=user_group,
                )
                job.full_clean()
                logger.debug(f'Adding new job: {job}')
                job.save()

                return HttpResponseRedirect(reverse('crontrack:view_jobs'))
        except KeyError:
            context['error_message'] = "missing required field(s)"
        except (CroniterBadCronError, IndexError):
            context['error_message'] = "invalid cron schedule string"
        except ValueError:
            # hopefully this can only happen for the int() call on time window
            context['error_message'] = "invalid time window"
        except ValidationError:
            # TODO: replace this with form validation
            context['error_message'] = "invalid data in one or more field(s)"
        
        return render(request, 'crontrack/addjob.html', context)
    else:
        return render(request, 'crontrack/addjob.html')
        
# ---- TODO: convert the context/error_message system to use django messages (?)
# Also make sure to redirect after successfully dealing with post data to prevent duplicates

@login_required
def edit_group(request):
    if request.method == 'POST' and request.user.is_authenticated and 'group' in request.POST:
        timezone.activate(request.user.timezone)
        context = {
            'group': get_job_group(request.user, request.POST['group'], request.POST['user_group']),
            'user_group': request.POST['user_group'],
        }
        if 'edited' in request.POST:
            # Submission after editing the group
            # Process the edit then return to view all jobs
            
            # Find user group
            if request.POST['user_group'] == 'None':
                user_group = None
            else:
                user_group = UserGroup.objects.get(pk=request.POST['user_group'])
            
            # Rename the job group / modify its description
            if request.POST['group'] == 'None':
                group = None
            else:
                try:
                    group = JobGroup.objects.get(pk=request.POST['group'])
                    if permission_denied(request.user, group.user, group.user_group):
                        logger.warning(f"User {request.user} tried to modify job group {group} without permission")
                        return render(request, 'crontrack/editgroup.html')
                    with transaction.atomic():
                        group.name = request.POST['group_name']
                        group.description = request.POST['description']
                        group.full_clean()
                        group.save()
                except ValidationError:
                    context['error_message'] = f"invalid group name/description"
                    return render(request, 'crontrack/editgroup.html', context)
            
            # Modify the jobs in the group
            pattern = re.compile(r'^([0-9a-z\-]+)__name')
            try:            
                for key in request.POST:
                    match = pattern.match(key)
                    if match:
                        with transaction.atomic():
                            job_id = match.group(1)
                            # Check if we're adding a new job (with a single number for its temporary ID)
                            if job_id.isdigit():
                                job = Job(user=request.user, group=group, user_group=user_group)
                            # Otherwise, find the existing job to edit
                            else:
                                job = Job.objects.get(id=job_id)
                                if permission_denied(request.user, job.user, job.user_group):
                                    logger.warning(f"User {request.user} tried to access job {job} without permission")
                                    return render(request, 'crontrack/editgroup.html')
                
                            job.name = request.POST[f'{job_id}__name']
                            job.schedule_str = request.POST[f'{job_id}__schedule_str']
                            job.time_window = int(request.POST[f'{job_id}__time_window'])
                            job.description = request.POST[f'{job_id}__description']
                            
                            now = timezone.localtime(timezone.now())
                            job.next_run = croniter(job.schedule_str, now).get_next(datetime)
                            job.full_clean()
                            job.save()                          
            except CroniterBadCronError:
                context['error_message'] = "invalid cron schedule string"
            except ValueError:
                context['error_message'] = "please enter a valid whole number for the time window"
            except ValidationError:
                context['error_message'] = "invalid data entered in one or more fields"
            else:
                return HttpResponseRedirect(reverse('crontrack:view_jobs'))
            
            return render(request, 'crontrack/editgroup.html', context)
        else:
            # First view of page with group to edit
            return render(request, 'crontrack/editgroup.html', context)
    
    return render(request, 'crontrack/editgroup.html')  

@login_required
def delete_group(request):
    if request.method == 'POST' and request.user.is_authenticated and 'group' in request.POST:
        try:
            group = JobGroup.objects.get(pk=request.POST['group'])
            if permission_denied(request.user, group.user, group.user_group):
                logger.warning(f"User {request.user} tried to delete job group {group} without permission")
            else:
                group.delete()
        except JobGroup.DoesNotExist:
            logger.exception(f"Tried to delete job group with id '{request.POST['group']}' and it didn't exist")
    
    return HttpResponseRedirect(reverse('crontrack:view_jobs'))
    
# Delete job with AJAX
@login_required
def delete_job(request):
    # Delete job and return to editing group
    if request.method == 'POST' and request.user.is_authenticated and 'itemID' in request.POST:
        try:
            job = Job.objects.get(pk=request.POST['itemID'])
            if permission_denied(request.user, job.user, job.user_group):
                logger.warning(f"User {request.user} tried to delete job {job} without permission")
            else:
                job.delete()
            data = {'itemID': request.POST['itemID']}
        except Job.DoesNotExist:
            print(f"ERROR: Tried to delete job with id '{request.POST['itemID']}' and it didn't exist " +
                f"(or didn't belong to the user '{request.user.username}')"
            )
        else:
            return JsonResponse(data)
    
    return HttpResponseRedirect(reverse('crontrack:view_jobs'))

@login_required
def user_groups(request):
    context = {}
    if request.method == 'POST' and 'type' in request.POST:
        if request.POST['type'] == 'create_group':
            group = None
            try:
                with transaction.atomic():
                    group = UserGroup(name=request.POST.get('group_name'), creator=request.user)
                    group.full_clean()
                    group.save()
                    UserGroupMembership.objects.create(user=request.user, group=group)
            except ValidationError:
                context['error_message'] = 'invalid group name'             
        elif request.POST['type'] == 'delete_group':
            UserGroup.objects.get(pk=request.POST['group_id']).delete()
        elif request.POST['type'] == 'toggle_alerts':
            if request.POST['group_id'] == 'None':
                request.user.personal_alerts_on = request.POST['alerts_on'] == 'true'
                request.user.save()
            else:
                group = UserGroup.objects.get(pk=request.POST['group_id'])
                membership = UserGroupMembership.objects.get(group=group, user=request.user)
                membership.alerts_on = request.POST['alerts_on'] == 'true'
                membership.save()
        else:
            try:
                user = User.objects.get(username=request.POST['username'])
                group = UserGroup.objects.get(pk=request.POST['group_id'])
            except User.DoesNotExist:
                context['error_message'] = f"no user found with username '{request.POST['username']}'"
            except UserGroup.DoesNotExist:
                pass
            else:
                if request.POST['type'] == 'add_user':
                    # Is it okay to add users to groups without them having a say?
                    # TODO: consider sending a popup etc. to the other user to confirm before adding them
                    UserGroupMembership.objects.create(user=user, group=group)
                elif request.POST['type'] == 'remove_user':
                    if user.id == group.creator.id:
                        context['error_message'] = "the group's creator cannot be removed from the group"
                    else:
                        UserGroupMembership.objects.get(user=user, group=group).delete()
    
    if request.is_ajax():
        return JsonResponse({})
    else:
        context['membership_alerts'] = {
            m.group.id for m in UserGroupMembership.objects.filter(user=request.user) if m.alerts_on
        }
        return render(request, 'crontrack/usergroups.html', context)

@login_required
def profile(request):
    context = {}
    if request.method == 'POST' and request.user.is_authenticated:
        form = ProfileForm(request.POST)
        
        if form.is_valid():
            # Update profile settings   
            request.user.timezone = form.cleaned_data['timezone']
            request.user.alert_method = form.cleaned_data['alert_method']
            request.user.alert_buffer = form.cleaned_data['alert_buffer']
            request.user.email = form.cleaned_data['email']
            request.user.phone = form.cleaned_data['full_phone']
            request.user.save()
            context['success_message'] = "Account settings updated."
        else:
            context['prefill'] = {'alert_method': form.data['alert_method']}
    else:
        form = ProfileForm()
        
    context['form'] = form
    return render(request, 'registration/profile.html', context)

def delete_account(request):
    context = {}
    if request.method == 'POST' and request.user.is_authenticated:
        logger.debug(f"Deleting user account '{request.user}'")
        request.user.delete()
        logout(request)
        context['success_message'] = "Account successfully deleted."
        
    return render(request, 'registration/deleteaccount.html', context)
        
class RegisterView(generic.CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy('crontrack:profile')
    template_name = 'registration/register.html'
    
    def form_valid(self, form):
        valid = super(RegisterView, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid


# --- HELPER FUNCTIONS ---

# Gets a user's job group information with their corresponding jobs
def get_job_group(user, job_group, user_group):
    # Try to convert the user group to an object
    if type(user_group) == str: 
        if user_group == 'None':
            user_group = None
        elif user_group.isdigit():
            # User group is an ID rather than an object
            user_group = UserGroup.objects.get(pk=user_group)
    
    # Check if we're looking at a real job group or the 'Ungrouped' group
    if job_group is None or job_group == 'None':
        jobs = Job.objects.filter(group__isnull=True)
        id = None
        name = 'Ungrouped'
        description = ''
        if user_group is None:
            jobs = jobs.filter(user=user, user_group__isnull=True)
        else:
            jobs = jobs.filter(user_group=user_group)
            
        # Skip showing the 'Ungrouped' group if it's empty
        if not jobs:
            return None
    else:
        # Try to convert the job group to an object
        if type(job_group) == str and job_group.isdigit():
            # Group is an ID rather than an object
            job_group = JobGroup.objects.get(pk=job_group)
            
        # Discard if the JobGroup's user_group doesn't match the given user_group
        if (user_group != job_group.user_group) or (job_group.user_group is None and user != job_group.user):
            return None
        
        jobs = Job.objects.filter(group=job_group.id)
        id = job_group.id
        name = job_group.name
        description = job_group.description
    
    return {'id': id, 'name': name, 'description': description, 'jobs': jobs, 'user_group': user_group}

# Checks if a user shouldn't be able to access a job (i.e. if they don't own it and aren't part of the group it's in)
def permission_denied(request_user, user, user_group):
    return request_user != user and user_group not in request_user.user_groups.all()