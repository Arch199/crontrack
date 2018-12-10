from django.db import models

class Job(models.Model):
	schedule_str = models.CharField('cron schedule string', max_length=100)
	name = models.CharField(max_length=50)
	time_window = models.IntegerField('time window (minutes)', default=0)
	next_run = models.DateTimeField('next time to run')
	last_notified = models.DateTimeField('last time notification received')
	description = models.CharField(max_length=200, blank=True, default='')
	
	""" TODO:
	- Add user account id to this model
	- Add a model for a user (logins and stuff? - auth can do that maybe)
	"""
	
	def __str__(self):
		return f'{self.name}: "{self.schedule_str}", {self.time_window}min window, next={self.next_run}, last={self.last_notified}'