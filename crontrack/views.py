from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils import timezone

from croniter import croniter  # see https://pypi.org/project/croniter/#usage
from datetime import datetime

from .models import Job

def index(request):
	jobs = Job.objects.all()
	context = {'jobs': jobs}
	return render(request, 'crontrack/viewjobs.html', context)
	
def add_job(request):
	if request.method == 'POST':
		# Logic to add the job
		# The request has everything but next_run and last_notified (need to calculate those)
		#for key in request.POST.keys():
		#	print(f'thing: "{key}" : "{request.POST[key]}"')
		#keys = list(request.POST.keys())
		#print(keys)
		
		#try:
		job = Job(
			name=request.POST['name'],
			schedule_str=request.POST['schedule_str'],
			time_window=request.POST['time_window'],
			description=request.POST['description'],
			next_run=croniter(request.POST['schedule_str'], timezone.now()).get_next(datetime),
			last_notified=timezone.now(),  # TODO: change default last_notified to null, etc. ?
		)
		print("Adding new job:", job)
		#job.save()
		
		return HttpResponseRedirect(request.path_info, {'success_message': "Job added successfully!"})
		#except KeyError:
		#	return render(request, 'crontrack/addjob.html', {'error_message': "missing required field(s)"})	
	else:
		return render(request, 'crontrack/addjob.html')