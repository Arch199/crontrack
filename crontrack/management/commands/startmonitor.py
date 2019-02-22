from django.core.management.base import BaseCommand, CommandError

from crontrack.background import JobMonitor

class Command(BaseCommand):
    help = "Start the job monitor."

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-for', '-s',
            type=int,
            default=None,
            dest='run-for',
            help="Time to run for in seconds. Defaults to forever.",
        )
        
    def handle(self, *args, **options):
        try:
            monitor = JobMonitor(options['run-for'])
        except ValueError as e:
            raise CommandError(str(e))