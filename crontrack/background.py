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

from .models import Job, JobAlert, User, UserGroupMembership

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
                    logger.debug(f"Alert! Job: {job} failed to notify in the time window")
                    
                    # Try alerting users in the relevant user group
                    if job.user_group is None:
                        users = (job.user,)
                    else:
                        users = job.user_group.user_set.all()
                    for user in users:
                        if user not in job.alerted_users.all():
                            # Send an alert if it's our first
                            JobAlert.objects.create(user=user, job=job, last_alert=timezone.now())
                            self.alert_user(user, job)
                        else:
                            # Otherwise, decide whether to skip alerting 
                            # (based on that user's alert_buffer setting and the last alert sent to them for this job)
                            buffer_time = timedelta(minutes=user.alert_buffer)
                            last_alert = JobAlert.objects.get(job=job, user=user).last_alert
                            if timezone.now() > last_alert + buffer_time:
                                self.alert_user(user, job)
                            else:
                                logger.debug(f"Skipped alerting user '{user}' of failed job {job}")
                
                # Calculate the new next run time
                timezone.activate(job.user.timezone)
                now = timezone.localtime(timezone.now())
                job.next_run = croniter(job.schedule_str, now).get_next(datetime)
                job.save()
                
            time.sleep(60)  # TODO: Put this back to 2*60 (2 min) or 1 min (?)
        
    def alert_user(self, user, job):        
        # Skip alerting if the user has alerts disabled (either globally or just for this user group
        if user.alert_method == User.NO_ALERTS:
            logger.debug(f"Not alerting user '{user}' as they have all alerts disabled")
            return
        if job.user_group is None:
            alerts_on = user.personal_alerts_on
        else:
            alerts_on = UserGroupMembership.objects.get(user=user, group=job.user_group).alerts_on
        if not alerts_on:
            logger.debug(f"Not alerting user '{user}' as they have alerts for group '{job.user_group}' disabled")
            return
        
        # Either send an email or text based on user preferences
        context = {'job': job, 'user': user, 'protocol': settings.SITE_PROTOCOL, 'domain': settings.SITE_DOMAIN}
        if user.alert_method == User.EMAIL:
            logger.debug(f"Sending user '{user}' an email at {user.email}")
            subject = f"[CronTrack] ALERT: Job '{job.name}' failed to notify in time"
            message = render_to_string('crontrack/email/alertuser.html', context)
            user.email_user(subject, strip_tags(message), html_message=message)
        else:
            logger.debug(f"Sending user '{user}' an SMS at {user.phone}")
            message = render_to_string('crontrack/sms/alertuser.txt', context)
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            try:
                client.messages.create(body=message, to=str(user.phone), from_=settings.TWILIO_FROM_NUMBER)
            except TwilioRestException:
                logger.exception(f"Failed to send user '{user.username}' an SMS at {user.phone}")
        
        JobAlert.objects.get(job=job, user=user).last_alert = timezone.now()
        job.save()