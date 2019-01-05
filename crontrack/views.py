from datetime import datetime
from itertools import chain
import re

import pytz
from croniter import croniter, CroniterBadCronError  # see https://pypi.org/project/croniter/#usage

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm  # from https://wsvincent.com/django-user-authentication-tutorial-signup/
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Job, JobGroup, User, Profile
from .forms import ProfileForm

def index(request):
	return render(request, 'crontrack/index.html')
	
# is exempting this from CSRF protection ok? 
@csrf_exempt
def notify_job(request, id):
	username = request.POST['username']
	password = request.POST['password']
	user = authenticate(request, username=username, password=password)
	data = {}
	if user is not None:
		try:
			job = Job.objects.get(pk=id, user=user)
			job.last_notified = timezone.now()
			job.save()
			if settings.DEBUG:
				print(f'Notified by user "{username}", job "{id}" at {job.last_notified}')
		except Job.DoesNotExist:
			data['error_message'] = f"Error: Job not found for UUID '{id}' and user '{username}'."
		finally:
			logout(request)
	else:
		data['error_message'] = "Error: invalid login credentials."
	return JsonResponse(data)

@login_required
def view_jobs(request):
	timezone.activate(request.user.profile.timezone)
	
	ungrouped = ([get_group(request.user, None)])
	grouped = (get_group(request.user, g) for g in JobGroup.objects.filter(user=request.user))
	context = {'groups': chain(ungrouped, grouped)}
	
	return render(request, 'crontrack/viewjobs.html', context)

@login_required
def add_job(request):
	if request.method == 'POST':
		context = {'prefill': request.POST}
		# Logic to add the job
		try:
			now = datetime.now(tz=pytz.timezone(request.POST['timezone']))
			
			# Check if we're adding a group
			if 'group' in request.POST:
				with transaction.atomic():
					if not request.POST['name']:
						raise KeyError
					group = JobGroup(
						user=request.user,
						name=request.POST['name'],
						description=request.POST['description'],
					)
					if settings.DEBUG:
						print("Adding new group:", group)
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
						job = Job(
							user=request.user,
							name=job_name,
							schedule_str=schedule_str,
							time_window=int(request.POST['time_window']),
							next_run=croniter(schedule_str, now).get_next(datetime),
							group=group,
						)
						if settings.DEBUG:
							print("Adding new job:", job)
						have_added_job = True
						job.save()
					if not have_added_job:
						# We didn't get any jobs
						context['error_message'] = "no valid jobs entered"
						#return HttpResponseRedirect('/crontrack/viewjobs')
						return render(request, 'crontrack/addjob.html', context)
					
					# Group added successfully, open it up for editing
					context = {'group': get_group(request.user, group)}
					return render(request, 'crontrack/editgroup.html', context)
			
			# Otherwise, just add the single job
			else:
				job = Job(
					user=request.user,
					name=request.POST['name'],
					schedule_str=request.POST['schedule_str'],
					time_window=int(request.POST['time_window']),
					description=request.POST['description'],
					next_run=croniter(request.POST['schedule_str'], now).get_next(datetime),
				)
				if settings.DEBUG:
					print("Adding new job:", job)
				job.save()

				return HttpResponseRedirect('/crontrack/viewjobs')
		except KeyError:
			context['error_message'] = "missing required field(s)"
		except (CroniterBadCronError, IndexError):
			context['error_message'] = "invalid cron schedule string"
		except ValueError:
			# hopefully this can only happen for the int() call on time window
			context['error_message'] = "invalid time window"
		
		return render(request, 'crontrack/addjob.html', context)
	else:
		return render(request, 'crontrack/addjob.html')
		
# ---- TODO: convert the context/error_message system to use django messages (?)
# Also make sure to redirect after successfully dealing with post data to prevent duplicates

@login_required
def edit_group(request):
	if request.method == 'POST' and request.user.is_authenticated and 'group' in request.POST:
		timezone.activate(request.user.profile.timezone)
		context = {'group': get_group(request.user, request.POST['group'])}
		if 'edited' in request.POST:
			# Submission after editing the group
			# Process the edit then return to view all jobs
			
			#context = {key: request.POST[key] for key in request.POST if key != 'edited'}
			# TODO: add some kind of prefill (with a form?)
			
			# Rename the group / modify its description
			if request.POST['group'] != 'None':
				try:
					group = JobGroup.objects.get(pk=request.POST['group'], user=request.user)
					with transaction.atomic():
						group.name = request.POST['group_name']
						group.description = request.POST['description']
						group.full_clean()
						group.save()
				except ValidationError:
					context['error_message'] = f"invalid group name '{request.POST['group_name']}'"
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
								job = Job(
									user=request.user,
									group=JobGroup.objects.get(pk=request.POST['group']),
								)
							# Otherwise, find the existing job to edit
							else:
								job = Job.objects.get(id=job_id)
								assert job.user == request.user  # TODO: handle this better?
				
							job.name = request.POST[f'{job_id}__name']
							job.schedule_str = request.POST[f'{job_id}__schedule_str']
							job.time_window = int(request.POST[f'{job_id}__time_window'])
							job.description = request.POST[f'{job_id}__description']
							
							now = timezone.localtime(timezone.now())
							job.next_run = croniter(job.schedule_str, now).get_next(datetime)
							
							# Note: removed this for being unecessary
							"""tz = request.user.profile.timezone
							format = '%Y-%m-%dT%H:%M'
							job.last_notified = tz.localize(datetime.strptime(request.POST[f'{job_id}__last_notified'], format))
							job.next_run = tz.localize(datetime.strptime(request.POST[f'{job_id}__next_run'], format))"""
						
							# TODO: Add a form class for validation (this is kinda ugly as is)
							# see https://docs.djangoproject.com/en/2.1/topics/forms/
							
							job.full_clean()
							job.save()
			except CroniterBadCronError:
				context['error_message'] = "invalid cron schedule string"
			except ValueError:
				context['error_message'] = "please enter a valid whole number for the time window"  #TODO: check if this can be called by other fields
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
			group = JobGroup.objects.get(pk=request.POST['group'], user=request.user)
			group.delete()
		except JobGroup.DoesNotExist:
			print(
				f"ERROR: Tried to delete job group with id '{request.POST['group']}' and it didn't exist "
				"(or didn't belong to the user '{request.user.username}')"
			)
	
	return HttpResponseRedirect('/crontrack/viewjobs')

# Delete job with AJAX
@login_required
def delete_job(request):
	# Delete job and return to editing group
	if request.method == 'POST' and request.user.is_authenticated and 'itemID' in request.POST:
		try:
			job = Job.objects.get(pk=request.POST['itemID'], user=request.user)
			job.delete()
			data = {'itemID': request.POST['itemID']}
		except Job.DoesNotExist:
			print(f"ERROR: Tried to delete job with id '{request.POST['itemID']}' and it didn't exist (or didn't belong to the user '{request.user.username}')")
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
			profile.save()
			
			request.user.email = form.cleaned_data['email']
			request.user.save()
			context['success_message'] = "Account settings updated."
			
			"""
			try:
				profile.timezone = request.POST['timezone']
				profile.full_clean()
				profile.save()
				context['success_message'] = "Account settings updated."
			except ValidationError:
				context['error_message'] = "invalid timezone; please select from the list"
			"""
	else:
		form = ProfileForm(initial={'timezone': request.user.profile.timezone})
		
	context['form'] = form
	return render(request, 'registration/profile.html', context)

class Register(generic.CreateView):  # TODO: consider making a separate accounts app for this stuff
	form_class = UserCreationForm
	success_url = '/crontrack/accounts/profile'
	template_name = 'registration/register.html'
	
	# from https://stackoverflow.com/questions/26510242/django-how-to-login-user-directly-after-registration-using-generic-createview
	def form_valid(self, form):
		valid = super(Register, self).form_valid(form)
		username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
		new_user = authenticate(username=username, password=password)
		login(self.request, new_user)
		return valid


# --- HELPER FUNCTIONS ---

# Gets a user's job group information with their corresponding jobs
def get_group(user_id, group):
	if group is None or group == 'None':
		jobs = Job.objects.filter(user=user_id, group__isnull=True)
		return {'id': None, 'name': 'Ungrouped', 'description': '', 'jobs': jobs}
	else:
		if type(group) == str and group.isdigit():
			# Group is an ID rather than an object
			group = JobGroup.objects.get(user=user_id, id=group)
		
		jobs = Job.objects.filter(user=user_id, group=group.id)
		return {'id': group.id, 'name': group.name, 'description': group.description, 'jobs': jobs}