from django.core.management.base import BaseCommand

from crontrack.background import JobMonitor

class Command(BaseCommand):
    help = "Start the job monitor."

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-for', '-s',
            type=int,
            default=None,
            dest='run-for',
            help='Time to run for in seconds. Defaults to forever.'
        )
        
    def handle(self, *args, **options):
        time_limit = options.get('run-for', None)
        if time_limit is None or time_limit > 0:
            self.stdout.write(self.style.SUCCESS("Successfully started the job monitor"))
            monitor = JobMonitor(time_limit)
            
            # Wait around to keep this thread open
            while True:
                pass
        else:
            self.stdout.write(self.style.ERROR("Argument '--run-for, -s' must be a positive number of seconds"))