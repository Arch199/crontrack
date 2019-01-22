# Background Tasks (main loop logic for job notification handling)
import time
import threading
import logging
from datetime import datetime, timedelta

from croniter import croniter
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from django.core import mail
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from django.template.loader import render_to_string

from .models import Job, Profile

logger = logging.getLogger(__name__)

class JobMonitor:
	def __init__(self):
		logger.debug('Starting JobMonitor thread')
		self.t = threading.Thread(target=self.monitor, name='JobMonitorThread', daemon=True)
		self.t.start()
	
	def monitor(self):		
		while True:
			logger.debug(f'Starting monitor loop at {timezone.now()}')
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
				
			time.sleep(60)  # TODO: Put this back to 2*60 (2 min) or 1 min (?)
		
	def alertUser(self, job):
		#DEBUG <- TODO: remove
		if job.user.username != 'eggman':
			#print('Was gonna alert but noped out for james')
			return
			
		logger.debug(f'Alert! Job: {job} failed to notify in the time window.')
		
		# Either send an email or text based on user preferences
		context = {'job': job, 'domain': settings.DEFAULT_SITE_URL}
		if job.user.profile.alert_method == Profile.EMAIL:
			logger.debug(f'Sending user "{job.user.username}" an email at {job.user.email}')
			subject = f'[CronTrack] ALERT: Job "{job.name}" failed to notify within time window',
			message = render_to_string('crontrack/email/alertuser.html', context)
			job.user.email_user(subject, strip_tags(message), html_message=message)
		else:
			logger.debug(f'Sending user "{job.user.username}" an SMS at {job.user.profile.phone}')
			message = render_to_string('crontrack/sms/alertuser.html', context)
			client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
			try:
				print(f'{len(message)} :: {message}')
				client.messages.create(body=message, to=str(job.user.profile.phone), from_=settings.TWILIO_FROM_NUMBER)
			except TwilioRestException:
				logger.exception('Failed to send user "{job.user.username}" an SMS at {job.user.profile.phone}')