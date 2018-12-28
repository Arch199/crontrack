from django.apps import AppConfig

class CrontrackConfig(AppConfig):
	name = 'crontrack'
	
	def ready(self):
		import crontrack.signals
		import crontrack.background