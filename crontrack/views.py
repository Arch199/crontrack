from datetime import datetime

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm  # from https://wsvincent.com/django-user-authentication-tutorial-signup/
from django.views import generic
from django.core.exceptions import ValidationError

from croniter import croniter, CroniterBadCronError  # see https://pypi.org/project/croniter/#usage

from .models import Job, User, Profile

def index(request):
	return render(request, 'crontrack/index.html')

def view_jobs(request):
	context = {'jobs': Job.objects.filter(user=request.user.id)}
	return render(request, 'crontrack/viewjobs.html', context)
	
def add_job(request):
	if request.method == 'POST':
		# Logic to add the job
		try:
			job = Job(
				user = request.user,
				name=request.POST['name'],
				schedule_str=request.POST['schedule_str'],
				time_window=int(request.POST['time_window']),
				description=request.POST['description'],
				next_run=croniter(request.POST['schedule_str'], timezone.now()).get_next(datetime),
				last_notified=timezone.now(),  # TODO: change default last_notified to null, etc. ?
			)                                  # TODO: make timezones work + user accounts
			if settings.DEBUG:
				print("Adding new job:", job)
			job.save()
			
			context = {'success_message': "Job added successfully!"}
		except KeyError:
			context = {'error_message': "missing required field(s)", 'prefill': request.POST}
		except ValueError:
			context = {'error_message': "invalid time window", 'prefill': request.POST}
			# ^ hopefully this can only happen for the int() call on time window
		except CroniterBadCronError:
			context = {'error_message': "invalid cron schedule string", 'prefill': request.POST}
		finally:
			#return HttpResponseRedirect(request.path_info, context) #<--doesn't keep request.POST in scope
			return render(request, 'crontrack/addjob.html', context)
	else:
		return render(request, 'crontrack/addjob.html')

def profile(request):
	context = {}
	if request.method == 'POST' and request.user.is_authenticated:
		context['prefill'] = request.POST
		
		# Update profile settings
		try:
			profile = User.objects.get(pk=request.user.id).profile
			#print("profile type",type(profile))
			#print('profile:',profile)
		except Profile.DoesNotExist:
			profile = Profile(user=request.user)
		
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
	success_url = '/crontrack/viewjobs'
	template_name = 'registration/register.html'
	
"""	
#def log_in(request):	
#	return render(request, 'crontrack/login.html')

class LogIn(LoginView):
	template_name = 'crontrack/login.html'
	redirect_field_name = 'account.html'

def register(request):
	if request.method == 'POST':
		pass #TODO: add this?
	else:
		return render(request, 'registration/register.html')"""