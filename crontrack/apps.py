import os

from django.apps import AppConfig
from django.conf import settings

class CronTrackConfig(AppConfig):
	name = 'crontrack'
	
	def ready(self):
		import crontrack.signals
		import crontrack.background
		
		# Only run the monitor in the main thread
		if os.environ.get('RUN_MAIN') == 'true':
			monitor = crontrack.background.JobMonitor()