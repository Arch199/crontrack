# CronTrack

This Django app allows you to (or will allow you to, currently WIP) enter and keep track of Cron jobs with a set schedule and time window for completion, with an automatic email/text (configurable) being sent to you if the job doesn't complete successfully. This is accomplished by adding an API call to your code that notifies CronTrack when it has completed (so that if it doesn't receive a notification, it can send you a message).
