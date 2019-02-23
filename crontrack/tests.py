import logging
import random
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, SimpleTestCase
from django.utils import timezone

from .background import JobMonitor
from .models import Job, User, Team, TeamMembership

logging.disable(logging.INFO)


class JobTestCase(SimpleTestCase):
    def test_failing(self):
        false_cases = (
            Job(last_failed=timezone.now()),
            Job(next_run=timezone.now()+timedelta(seconds=1)),
            Job(next_run=timezone.now()),
        )
        for job in false_cases:
            self.assertEqual(job.failing, False)
        
        true_cases = (
            Job(next_run=timezone.now()-timedelta(seconds=1), last_notified=None),
            Job(next_run=timezone.now()-timedelta(minutes=1), last_notified=timezone.now()-timedelta(minutes=2)),
        )
        for job in true_cases:
            self.assertEqual(job.failing, True)


class JobMonitorTestCase(TestCase):
    def test_validation(self):
        self.assertRaises(ValueError, JobMonitor, time_limit=0)
        self.assertRaises(ValueError, JobMonitor, time_limit=-5)
    
    def test_stopping(self):
        monitor = JobMonitor()
        monitor.stop()
        self.assertEqual(monitor.running, False)
        
        monitor = JobMonitor(time_limit=JobMonitor.WAIT_INTERVAL, threaded=False)
        self.assertEqual(monitor.running, False)
        
        monitor = JobMonitor(time_limit=JobMonitor.WAIT_INTERVAL+1, threaded=True)
        self.assertEqual(monitor.running, True)
        monitor.stop()
        self.assertEqual(monitor.running, False)
        

class UserTestCase(TestCase):
    def setup(self):
        users = {
            'alice': User.objects.create(username='alice'),
            'bob': User.objects.create(username='bob'),
            'carl': User.objects.create(username='carl'),
        }
        teams = (
            Team.objects.create(name='generic name', creator=alice),
            Team.objects.create(name='the sequel', creator=bob),
            Team.objects.create(name='headless chicken', creator=None),
        )
        TeamMembership.objects.create(user=alice, team=teams[0])
        TeamMembership.objects.create(user=bob, team=teams[0])
        TeamMembership.objects.create(user=bob, team=team[1])
        
        for i in range(10):
            Job.objects.create(user=random.choice(users), team=random.choice(teams))
        
    def test_job_access(self):
        for user in User.objects.all():
            my_jobs = user.all_accessible(Job)
            for job in Job.objects.all():
                self.assertEqual(user.can_access(job), job in my_jobs) 
        