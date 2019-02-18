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
from .models import Job, JobGroup, JobAlert, User, Team, TeamMembership

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'crontrack/index.html')

def notify_job(request, id):
    job = Job.objects.get(pk=id)
    job.last_notified = timezone.now()
    job.last_failed = None
    job.save()
    logger.debug(f"Notified for job '{id}' at {job.last_notified}")
    
    return JsonResponse({'success_message': 'Job notified successfully.'})

@login_required
def view_jobs(request):
    timezone.activate(request.user.timezone)
    
    context = {
        'teams': [{'id': 'All', 'job_groups': [], 'empty': True}],
        'protocol': settings.SITE_PROTOCOL,
        'domain': settings.SITE_DOMAIN
    }
    for team in chain((None,), request.user.teams.all()):
        ungrouped = (get_job_group(request.user, None, team),)
        grouped = (get_job_group(request.user, g, team) for g in JobGroup.objects.all())
        
        if team is None:
            id = None
        else:
            id = team.id
        job_groups = [group for group in chain(ungrouped, grouped) if group is not None]
        empty = not any(group['jobs'] for group in job_groups)
        
        context['teams'].append({'id': id, 'job_groups': job_groups, 'empty': empty})
        context['teams'][0]['job_groups'] += job_groups
        context['teams'][0]['empty'] = empty and context['teams'][0]['empty']
    
    return render(request, 'crontrack/viewjobs.html', context)

@login_required
def add_job(request):
    if request.method == 'POST':
        context = {'prefill': request.POST}
        # Logic to add the job
        try:
            now = datetime.now(tz=pytz.timezone(request.POST['timezone']))
            
            # Determine which team we're adding to
            if request.POST['team'] == 'None':
                team = None
            else:
                team = Team.objects.get(pk=request.POST['team'])
                if team not in request.user.teams.all():
                    team = None
                    logger.warning(f"User {request.user} tried to access a team they're not in: {team}")
            
            # Check if we're adding a group
            if 'group' in request.POST:
                with transaction.atomic():
                    group = JobGroup(
                        user=request.user,
                        name=request.POST['name'],
                        description=request.POST['description'],
                        team=team,
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
                            team=team,
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
                    context = {'group': get_job_group(request.user, group, team)}
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
                    team=team,
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
def edit_job(request):
    if request.method == 'POST':
        job = Job.objects.get(pk=request.POST['job'])
        if 'edited' in request.POST:
            # Edit the job
            context = {'prefill': request.POST}
            try:
                with transaction.atomic():
                    job.name = request.POST['name']
                    job.schedule_str = request.POST['schedule_str']
                    job.time_window = request.POST['time_window']
                    job.description = request.POST['description']
                    
                    timezone.activate(request.user.timezone)
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
                
            # ^ copied code feels bad. TODO: draw this out into a helper function
            return render(request, 'crontrack/editjob.html', context)
        else:
            return render(request, 'crontrack/editjob.html', {'job': job})
    else:
        return render(request, 'crontrack/editjob.html')

@login_required
def edit_group(request):
    if request.method == 'POST' and request.user.is_authenticated and 'group' in request.POST:
        timezone.activate(request.user.timezone)
        context = {
            'group': get_job_group(request.user, request.POST['group'], request.POST['team']),
            'team': request.POST['team'],
        }
        if 'edited' in request.POST:
            # Submission after editing the group
            # Process the edit then return to view all jobs
            
            # Find team
            if request.POST['team'] == 'None':
                team = None
            else:
                team = Team.objects.get(pk=request.POST['team'])
            
            # Rename the job group / modify its description
            if request.POST['group'] == 'None':
                group = None
            else:
                try:
                    group = JobGroup.objects.get(pk=request.POST['group'])
                    if permission_denied(request.user, group.user, group.team):
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
                                job = Job(user=request.user, group=group, team=team)
                            # Otherwise, find the existing job to edit
                            else:
                                job = Job.objects.get(id=job_id)
                                if permission_denied(request.user, job.user, job.team):
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
            if permission_denied(request.user, group.user, group.team):
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
            if permission_denied(request.user, job.user, job.team):
                logger.warning(f"User {request.user} tried to delete job {job} without permission")
            else:
                job.delete()
            data = {'itemID': request.POST['itemID']}
        except Job.DoesNotExist:
            logger.debug(
                f"Tried to delete job with id '{request.POST['itemID']}' and it didn't exist " +
                f"(or didn't belong to the user '{request.user}')"
            )
        else:
            return JsonResponse(data)
    
    return HttpResponseRedirect(reverse('crontrack:view_jobs'))

@login_required
def teams(request):
    context = {}
    if request.method == 'POST' and 'type' in request.POST:
        if request.POST['type'] == 'create_team':
            team = None
            try:
                with transaction.atomic():
                    team = Team(name=request.POST.get('team_name'), creator=request.user)
                    team.full_clean()
                    team.save()
                    TeamMembership.objects.create(user=request.user, team=team)
            except ValidationError:
                context['error_message'] = 'invalid team name'
        elif request.POST['type'] == 'delete_team':
            Team.objects.get(pk=request.POST['team_id']).delete()
        elif request.POST['type'] == 'toggle_alerts':
            if request.POST['team_id'] == 'None':
                request.user.personal_alerts_on = request.POST['alerts_on'] == 'true'
                request.user.save()
            else:
                team = Team.objects.get(pk=request.POST['team_id'])
                membership = TeamMembership.objects.get(team=team, user=request.user)
                membership.alerts_on = request.POST['alerts_on'] == 'true'
                membership.save()
        else:
            try:
                user = User.objects.get(username=request.POST['username'])
                team = Team.objects.get(pk=request.POST['team_id'])
            except User.DoesNotExist:
                context['error_message'] = f"no user found with username '{request.POST['username']}'"
            except Team.DoesNotExist:
                pass
            else:
                if request.POST['type'] == 'add_user':
                    # Is it okay to add users to teams without them having a say?
                    # TODO: consider sending a popup etc. to the other user to confirm before adding them
                    TeamMembership.objects.create(user=user, team=team)
                elif request.POST['type'] == 'remove_user':
                    if user.id == team.creator.id:
                        context['error_message'] = "the team's creator cannot be removed from the team"
                    else:
                        TeamMembership.objects.get(user=user, team=team).delete()
    
    if request.is_ajax():
        return JsonResponse({})
    else:
        context['membership_alerts'] = {
            m.team.id for m in TeamMembership.objects.filter(user=request.user) if m.alerts_on
        }
        return render(request, 'crontrack/teams.html', context)

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
def get_job_group(user, job_group, team):
    # Try to convert the team to an object
    if type(team) == str: 
        if team == 'None':
            team = None
        elif team.isdigit():
            # team is an ID rather than an object
            team = Team.objects.get(pk=team)
    
    # Check if we're looking at a real job group or the 'Ungrouped' group
    if job_group is None or job_group == 'None':
        jobs = Job.objects.filter(group__isnull=True)
        id = None
        name = 'Ungrouped'
        description = ''
        if team is None:
            jobs = jobs.filter(user=user, team__isnull=True)
        else:
            jobs = jobs.filter(team=team)
            
        # Skip showing the 'Ungrouped' group if it's empty
        if not jobs:
            return None
    else:
        # Try to convert the job group to an object
        if type(job_group) == str and job_group.isdigit():
            # Group is an ID rather than an object
            job_group = JobGroup.objects.get(pk=job_group)
            
        # Discard if the JobGroup's team doesn't match the given team
        if (team != job_group.team) or (job_group.team is None and user != job_group.user):
            return None
        
        jobs = Job.objects.filter(group=job_group.id)
        id = job_group.id
        name = job_group.name
        description = job_group.description
    
    return {'id': id, 'name': name, 'description': description, 'jobs': jobs, 'team': team}

# Checks if a user shouldn't be able to access a job (i.e. if they don't own it and aren't part of the team it's in)
def permission_denied(request_user, user, team):
    return request_user != user and team not in request_user.teams.all()