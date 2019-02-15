from django.core.management.base import BaseCommand

import crontrack.background as bg

class Command(BaseCommand):
    help = "Stop the job monitor."
    
    def handle(self, *args, **options):
        if bg.monitor_instance is not None:
            bg.monitor_instance.stop()
            self.stdout.write(self.style.SUCCESS("Successfully stopped the job monitor instance"))
        else:
            self.stdout.write(self.style.ERROR("The job monitor is not currently running"))