import uuid

from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from timezone_field import TimeZoneField
from phonenumber_field.modelfields import PhoneNumberField

class UserGroup(models.Model):
	name = models.CharField(max_length=50)
	creator = models.ForeignKey(User, models.CASCADE)
	
	def __str__(self):
		return self.name

class JobGroup(models.Model):
	name = models.CharField(max_length=50)
	description = models.CharField(max_length=200, blank=True, default='')
	user = models.ForeignKey(User, models.CASCADE)
	user_group = models.ForeignKey(UserGroup, models.SET_NULL, null=True, blank=True)
	
	def __str__(self):
		return f'{self.user}\'s {self.name}'

class Job(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	schedule_str = models.CharField('cron schedule string', max_length=100)
	name = models.CharField(max_length=50)
	time_window = models.IntegerField('time window (minutes)', default=0, validators=[MinValueValidator(0)])
	next_run = models.DateTimeField('next time to run')
	last_notified = models.DateTimeField('last time notification received', null=True, blank=True)
	last_alert = models.DateTimeField('last time alert sent', null=True, blank=True)
	description = models.CharField(max_length=200, blank=True, default='')
	user = models.ForeignKey(User, models.CASCADE)
	group = models.ForeignKey(JobGroup, models.CASCADE, null=True, blank=True)
	user_group = models.ForeignKey(UserGroup, models.SET_NULL, null=True, blank=True)
	
	def __str__(self):
		return f'{self.user}\'s {self.name}: "{self.schedule_str}"'
		
class Profile(models.Model):
	EMAIL = 'E'
	SMS = 'T'
	ALERT_METHOD_CHOICES = (
		(EMAIL, 'Email'),
		(SMS, 'SMS'),
	)
	user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
	timezone = TimeZoneField(default='UTC')
	alert_method = models.CharField(max_length=1, choices=ALERT_METHOD_CHOICES, default=EMAIL)
	alert_buffer = models.IntegerField('time to wait between alerts (min)', default=1440)
	phone = PhoneNumberField(blank=True)
	groups = models.ManyToManyField(UserGroup)