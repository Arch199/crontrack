# Background Tasks (main loop logic for job notification handling)
import time
from datetime import datetime, timedelta
import threading

from croniter import croniter

from django.core import mail
from django.conf import settings
from django.utils import timezone

from .models import Job, Profile

class JobMonitor:
	def __init__(self):
		self.t = threading.Thread(target=self.monitor)
		self.t.setDaemon(True)
		self.t.start()
	
	def monitor(self):		
		while True:
			if settings.DEBUG:
				print('Starting monitor loop')
			
			for job in Job.objects.all():
				# Calculate the next scheduled run time + time window
				run_by = job.next_run + timedelta(minutes=job.time_window)
				
				# Skip if this run time is in the future
				if run_by > timezone.now():
					continue
				
				# Check if a notification was not received in the time window
				if job.last_notified is None or not (job.next_run <= job.last_notified <= run_by):
					# Error condition: the job did not send a notification
					self.alertUser(job)
				
				# Calculate the new next run time
				timezone.activate(job.user.profile.timezone)
				now = timezone.localtime(timezone.now())
				job.next_run = croniter(job.schedule_str, now).get_next(datetime)
				job.save()
				
			time.sleep(10)
		
	def alertUser(self, job):
		#DEBUG
		if job.user.username != 'eggman':
			print('Was gonna alert but noped out for james')
			return
		
		# Either send an email or text based on user preferences
		if settings.DEBUG:
			print(f'Alert! Job: {job} failed to notify in the time window.')
		
		# TODO: remove DEBUG option
		if job.user.profile.alert_method == Profile.EMAIL:
			print('Emailing user about it')
			job.user.email_user(
				f'ALERT: Job "{job.name}" failed to notify within time window',
				# TODO: should probably make an email template
				f'''
					Dear {job.user.username},

					Your job "{job.name}" with scheule string "{job.schedule_str}" has failed to notify CronTrack.
					
					Job Run Time: {job.next_run}
					Time Window: {job.time_window} minutes
					
					Go to <a href="http://127.0.0.1:8000/crontrack/viewjobs">http://127.0.0.1:8000/crontrack/viewjobs</a> for more details.
				''',
			)

if not settings.RUNNING_SHELL:
	monitor = JobMonitor()