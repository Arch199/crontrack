# Background Tasks (main loop logic for job notification handling)
import time
from datetime import datetime, timedelta
import threading

from croniter import croniter

from django.conf import settings
from django.utils import timezone

from .models import Job

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
				
				# Keep going if this run time is in the future
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
				
			time.sleep(10)
		
	def alertUser(self, job):
		# Either send an email or text based on user preferences
		# TODO
		print(f'Alert! Job: {job} failed to notify in the time window.')
		
#monitor = JobMonitor()