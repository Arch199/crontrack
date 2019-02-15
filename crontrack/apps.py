import os

from django.apps import AppConfig
from django.conf import settings
from django.core import management

class CronTrackConfig(AppConfig):
    name = 'crontrack'
    
    def ready(self):        
        # Only run the monitor in the main thread
        if settings.JOB_MONITOR_ON and os.environ.get('RUN_MAIN') == 'true':
            with open(os.devnull, 'w') as devnull:
                management.call_command('startmonitor', stdout=devnull)