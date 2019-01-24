import re
import logging
from datetime import datetime
from itertools import chain

import pytz
from croniter import croniter, CroniterBadCronError  # see https://pypi.org/project/croniter/#usage

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Job, JobGroup, User, Profile, UserGroup
from .forms import ProfileForm

logger = logging.getLogger(__name__)

def index(request):
	return render(request, 'crontrack/index.html')

@csrf_exempt
def notify_job(request, id):
	data = {}
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(request, username=username, password=password)
		if user is not None:
			try:
				job = Job.objects.get(pk=id, user=user)
				job.last_notified = timezone.now()
				job.save()
				logger.debug(f'Notified by user "{username}", job "{id}" at {job.last_notified}')
			except Job.DoesNotExist:
				data['error_message'] = f"Error: job not found for UUID '{id}' and user '{username}'."
			finally:
				logout(request)
		else:
			data['error_message'] = "Error: invalid login credentials."
	else:
		data['error_message'] = "Error: request must be a POST request."
	
	return JsonResponse(data)

@login_required
def view_jobs(request):
	timezone.activate(request.user.profile.timezone)
	
	context = {'user_groups': []}
	for user_group in chain((None,), request.user.profile.groups.all()):
		ungrouped = (get_job_group(request.user, None, user_group),)
		grouped = (get_job_group(request.user, g, user_group) for g in JobGroup.objects.all())
		
		if user_group is None:
			id = 0
		else:
			id = user_group.id
		job_groups = [group for group in chain(ungrouped, grouped) if group is not None]
		empty = not any((group['jobs'] for group in job_groups))
		
		context['user_groups'].append({'id': id, 'job_groups': job_groups, 'empty': empty})
	
	return render(request, 'crontrack/viewjobs.html', context)

@login_required
def add_job(request):
	if request.method == 'POST':
		context = {'prefill': request.POST}
		# Logic to add the job
		try:
			now = datetime.now(tz=pytz.timezone(request.POST['timezone']))
			
			# Determine which user group we're adding to
			if request.POST['user_group'] == '':
				user_group = None
			else:
				user_group = UserGroup.objects.get(pk=request.POST['user_group'])
				if user_group not in request.user.profile.groups.all():
					user_group = None
					logger.warning("User {request.user} tried to access a group they\'re not in: {user_group}")
			
			# Check if we're adding a group
			if 'group' in request.POST:
				with transaction.atomic():
					group = JobGroup(
						user=request.user,
						name=request.POST['name'],
						description=request.POST['description'],
						user_group=user_group,
					)
					logger.debug(f'Adding new group: {group}')
					group.save()
					
					job_name = '[unnamed job]'
					have_added_job = False
					for line in request.POST['group_schedule'].split('\n'):
						if not line or line[0] in (' ', '\t', '\r'):
							continue
						if line[0] == '#':
							job_name = line[1:].strip()
							continue
						
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
						logger.debug(f'Adding new job: {job}')
						have_added_job = True
						job.save()
					if not have_added_job:
						# We didn't get any jobs
						context['error_message'] = "no valid jobs entered"
						#return HttpResponseRedirect('/crontrack/viewjobs')
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
				logger.debug(f'Adding new job: {job}')
				job.save()

				return HttpResponseRedirect('/crontrack/viewjobs')
		except KeyError:
			context['error_message'] = "missing required field(s)"
		except (CroniterBadCronError, IndexError):
			context['error_message'] = "invalid cron schedule string"
		except ValueError:
			# hopefully this can only happen for the int() call on time window
			context['error_message'] = "invalid time window"
		except UserGroup.DoesNotExist:
			context['error_message'] = f"no such user group '{request.POST['user_group']}'"
		
		return render(request, 'crontrack/addjob.html', context)
	else:
		return render(request, 'crontrack/addjob.html')
		
# ---- TODO: convert the context/error_message system to use django messages (?)
# Also make sure to redirect after successfully dealing with post data to prevent duplicates

@login_required
def edit_group(request):
	if request.method == 'POST' and request.user.is_authenticated and 'group' in request.POST:
		timezone.activate(request.user.profile.timezone)
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
				return HttpResponseRedirect('/crontrack/viewjobs')
			
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
	
	return HttpResponseRedirect('/crontrack/viewjobs')
	
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
	
	return HttpResponseRedirect('/crontrack/viewjobs')

@login_required
def profile(request):
	context = {}
	if request.method == 'POST' and request.user.is_authenticated:
		form = ProfileForm(request.POST)
		
		if form.is_valid():
			# Update profile settings
			profile = User.objects.get(pk=request.user.id).profile		
			profile.timezone = form.cleaned_data['timezone']
			profile.alert_method = form.cleaned_data['alert_method']
			profile.alert_buffer = form.cleaned_data['alert_buffer']
			profile.phone = form.cleaned_data['full_phone']
			profile.save()
			
			request.user.email = form.cleaned_data['email']
			request.user.save()
			context['success_message'] = "Account settings updated."
		else:
			context['prefill'] = {'alert_method': form.data['alert_method']}
	else:
		form = ProfileForm()
		
	context['form'] = form
	return render(request, 'registration/profile.html', context)
	
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
					request.user.profile.groups.add(group)
			except ValidationError:
				context['error_message'] = 'invalid group name'
		elif request.POST['type'] == 'delete_group':
			try:
				UserGroup.objects.get(pk=request.POST['group_id']).delete()
			except UserGroup.DoesNotExist:
				pass
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
					user.profile.groups.add(group)
				elif request.POST['type'] == 'remove_user':
					if user.id == group.creator.id:
						context['error_message'] = "you cannot remove yourself from a group you created"
					else:
						user.profile.groups.remove(group)
	
	return render(request, 'crontrack/usergroups.html', context)

class Register(generic.CreateView):
	form_class = UserCreationForm
	success_url = '/crontrack/accounts/profile'
	template_name = 'registration/register.html'
	
	def form_valid(self, form):
		valid = super(Register, self).form_valid(form)
		username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
		new_user = authenticate(username=username, password=password)
		login(self.request, new_user)
		return valid


# --- HELPER FUNCTIONS ---

# Gets a user's job group information with their corresponding jobs
def get_job_group(user_id, job_group, user_group):
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
			jobs = jobs.filter(user=user_id, user_group__isnull=True)
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
			
		# Check if the JobGroup's user_group matches the given user_group
		if (user_group != job_group.user_group) or (job_group.user_group is None and user_id != job_group.user.id):
			return None
		
		jobs = Job.objects.filter(group=job_group.id)
		id = job_group.id
		name = job_group.name
		description = job_group.description
	
	return {'id': id, 'name': name, 'description': description, 'jobs': jobs}

# Checks if a user shouldn't be able to modify a record (i.e. if they don't own it and aren't part of the group it's in)
def permission_denied(request_user, user, user_group):
	return request_user != user and user_group not in request_user.profile.groups.all()