import os

from django.apps import AppConfig
from django.conf import settings

class CronTrackConfig(AppConfig):
	name = 'crontrack'
	
	def ready(self):
		import crontrack.background
		
		# Only run the monitor in the main thread
		if settings.JOB_MONITOR_ON and os.environ.get('RUN_MAIN') == 'true':
			monitor = crontrack.background.JobMonitor()