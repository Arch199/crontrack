from datetime import timedelta
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import FieldError
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import date, time
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from timezone_field import TimeZoneField


class JobManager(models.Manager):
    def running(self):
        return self.get_queryset().filter(last_failed__isnull=True)

    def failed(self):
        return self.get_queryset().filter(last_failed__isnull=False)


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule_str = models.CharField('cron schedule string', max_length=100)
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True, default='')
    time_window = models.PositiveIntegerField('time window (minutes)', default=0)
    next_run = models.DateTimeField('next time to run')
    last_failed = models.DateTimeField('last time job failed to notify', null=True, blank=True)
    last_notified = models.DateTimeField('last time notification received', null=True, blank=True)
    
    user = models.ForeignKey('User', models.CASCADE)
    group = models.ForeignKey('JobGroup', models.CASCADE, null=True, blank=True)
    team = models.ForeignKey('Team', models.SET_NULL, null=True, blank=True)
    alerted_users = models.ManyToManyField('User', through='JobAlert', related_name='job_alert_set')

    objects = JobManager()
    
    def __str__(self):
        return f"({self.team}) {self.user}'s {self.name}: '{self.schedule_str}'"

    @property
    def failed(self):
        return bool(self.last_failed)

    @property
    def failing(self):
        # Checks if next_run has passed and a notification was not received, but it is still within the time window
        # Note: requires the job monitor to update last_failed to work correctly
        return (
            not self.failed and
            self.next_run < timezone.now() and
            (self.last_notified is None or self.last_notified < self.next_run)
        )


class JobGroup(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True, default='')
    user = models.ForeignKey('User', models.CASCADE)
    team = models.ForeignKey('Team', models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"({self.team}) {self.user}'s {self.name}"


class JobAlert(models.Model):
    job = models.ForeignKey('Job', models.CASCADE)
    user = models.ForeignKey('User', models.CASCADE)
    last_alert = models.DateTimeField('last time alert sent', null=True, blank=True)


class JobEvent(models.Model):
    FAILURE = 'F'
    WARNING = 'W'
    TYPE_CHOICES = (
        (FAILURE, 'Failure'),
        (WARNING, 'Warning'),
    )
    job = models.ForeignKey('Job', models.CASCADE, related_name='events')
    type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=FAILURE)
    time = models.DateTimeField()
    seen = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-time']


class User(AbstractUser):
    EMAIL = 'E'
    SMS = 'T'
    NO_ALERTS = 'N'
    ALERT_METHOD_CHOICES = (
        (EMAIL, 'Email'),
        (SMS, 'SMS'),
        (NO_ALERTS, 'No alerts'),
    )
    timezone = TimeZoneField(default='UTC')
    alert_method = models.CharField(max_length=1, choices=ALERT_METHOD_CHOICES, default=NO_ALERTS)
    alert_buffer = models.IntegerField('time to wait between alerts (min)', default=1440)
    personal_alerts_on = models.BooleanField('alerts on for jobs without a team', default=True)
    phone = PhoneNumberField(blank=True)
    email = models.EmailField(unique=True, max_length=100)
    teams = models.ManyToManyField('Team', through='TeamMembership')
    
    # Check if this user has access to an instance of a model (either Job or JobGroup)
    def can_access(self, instance):
        return instance.user == self or instance.team in self.teams.all()
    
    # Get all instances of a model this user has access to
    def all_accessible(self, model):
        try:
            return model.objects.filter(Q(user=self) | Q(team__in=self.teams.all()))
        except FieldError:
            # The model is connected to the user indirectly e.g. through a job like JobEvent
            return model.objects.filter(Q(job__user=self) | Q(job__team__in=self.teams.all()))


class Team(models.Model):
    name = models.CharField(max_length=50)
    creator = models.ForeignKey('User', models.CASCADE)
    
    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    user = models.ForeignKey('User', models.CASCADE)
    team = models.ForeignKey('Team', models.CASCADE)
    alerts_on = models.BooleanField(default=True)