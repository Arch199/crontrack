from datetime import datetime
from itertools import chain
import re

import pytz

from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm  # from https://wsvincent.com/django-user-authentication-tutorial-signup/
from django.views import generic
from django.core.exceptions import ValidationError
from django.db import transaction

from croniter import croniter, CroniterBadCronError  # see https://pypi.org/project/croniter/#usage

from .models import Job, JobGroup, User, Profile

def index(request):
	return render(request, 'crontrack/index.html')

def view_jobs(request):
	timezone.activate(request.user.profile.timezone)
	
	ungrouped = ([get_group(request.user, None)])
	grouped = (get_group(request.user, g) for g in JobGroup.objects.filter(user=request.user))
	context = {'groups': chain(ungrouped, grouped)}
	
	return render(request, 'crontrack/viewjobs.html', context)

def add_job(request):
	if request.method == 'POST':
		context = {'prefill': request.POST}
		#Logic to add the job
		try:
			now = datetime.now(tz=pytz.timezone(request.POST['timezone']))
			
			#Check if we're adding a group
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
							description=request.POST['description'],
							next_run=croniter(schedule_str, now).get_next(datetime),
							last_notified=now,  # TODO: change default last_notified to null, etc. ?
							group=group,
						)
						if settings.DEBUG:
							print("Adding new job:", job)
						have_added_job = True
						job.save()
					if not have_added_job:
						#We didn't get any jobs
						context['error_message'] = "no valid jobs entered"
						#return HttpResponseRedirect('/crontrack/viewjobs')
						return render(request, 'crontrack/addjob.html', context)
					
					#Group added successfully, open it up for editing
					context = {'group': get_group(request.user, group)}
					return render(request, 'crontrack/editgroup.html', context)
			
			#Otherwise, just add the single job
			else:
				job = Job(
					user=request.user,
					name=request.POST['name'],
					schedule_str=request.POST['schedule_str'],
					time_window=int(request.POST['time_window']),
					description=request.POST['description'],
					next_run=croniter(request.POST['schedule_str'], now).get_next(datetime),  #problem: this returns a naive datetime (?)
					last_notified=now,  # TODO: change default last_notified to null, etc. ?
				)
				if settings.DEBUG:
					print("Adding new job:", job)
				job.save()

				return HttpResponseRedirect('/crontrack/viewjobs')
		except KeyError:
			context['error_message'] = "missing required field(s)"
		except ValueError:
			# hopefully this can only happen for the int() call on time window
			context['error_message'] = "invalid time window"
		except (CroniterBadCronError, IndexError):
			context['error_message'] = "invalid cron schedule string"
		
		return render(request, 'crontrack/addjob.html', context)
	else:
		return render(request, 'crontrack/addjob.html')
		
# ---- TODO: convert the context/error_message system to use django messages (?)
# Also make sure to redirect after successfully dealing with post data to prevent duplicates

def edit_group(request):
	if request.method == 'POST' and request.user.is_authenticated:
		timezone.activate(request.user.profile.timezone)
		context = {'group': get_group(request.user, request.POST['group'])}
		if 'edited' in request.POST:
			#Submission after editing the group
			#Process the edit then return to view all jobs
			
			#context = {key: request.POST[key] for key in request.POST if key != 'edited'}
			# TODO: add some kind of prefill (with a form?)
			
			pattern = re.compile(r'^([0-9a-z\-]+)__')
			already_edited = []
			try:
				for key in request.POST:
					match = pattern.match(key)
					if match:
						job_id = match.group(1)
						if job_id in already_edited:
							continue
						job = Job.objects.get(id=job_id)
						assert job.user == request.user  # TODO: handle this better?
						
						with transaction.atomic():
							job.name = request.POST[f'{job_id}__name']
							job.schedule_str = request.POST[f'{job_id}__schedule_str']  # TODO: need to add Croniter validation
							job.time_window = request.POST[f'{job_id}__time_window']
							# --- TODO: add description and test this works --------------------------------
							
							# Note: removed this for being unecessary
							"""tz = request.user.profile.timezone
							format = '%Y-%m-%dT%H:%M'
							job.last_notified = tz.localize(datetime.strptime(request.POST[f'{job_id}__last_notified'], format))
							job.next_run = tz.localize(datetime.strptime(request.POST[f'{job_id}__next_run'], format))"""
						
							
							# TODO: Add a form class for validation (this is seriously ugly as is)
							# see https://docs.djangoproject.com/en/2.1/topics/forms/
							
							job.full_clean()
							job.save()
						
						already_edited.append(job_id)
				
			except ValidationError:
				context['error_message'] = "invalid data entered in one or more fields"
			else:
				return HttpResponseRedirect('/crontrack/viewjobs')
			
			return render(request, 'crontrack/editgroup.html', context)
		else:
			#First view of page with group to edit
			return render(request, 'crontrack/editgroup.html', context)
	return render(request, 'crontrack/editgroup.html')	
		
def profile(request):
	context = {}
	if request.method == 'POST' and request.user.is_authenticated:
		context['prefill'] = request.POST
		
		# Update profile settings
		profile = User.objects.get(pk=request.user.id).profile		
		try:
			profile.timezone = request.POST['timezone']
			profile.full_clean()
			profile.save()
			context['success_message'] = "Account settings updated."
		except ValidationError:
			context['error_message'] = "invalid timezone; please select from the list"

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
		
#Helper function for getting a user's job group information with their corresponding jobs
def get_group(user_id, group):
	if group is None or group == 'None':
		jobs = Job.objects.filter(user=user_id, group__isnull=True)
		return {'id': None, 'name': 'Ungrouped', 'description': '', 'jobs': jobs}
	else:
		if type(group) == str and group.isdigit():
			#Group is an ID rather than an object
			group = JobGroup.objects.get(user=user_id, id=group)
		
		jobs = Job.objects.filter(user=user_id, group=group.id)
		return {'id': group.id, 'name': group.name, 'description': group.description, 'jobs': jobs}