# CronTrack

[CronTrack](https://crontrack.com) is an open-source Django app for logging Cron jobs and keeping track of when they don't complete on time. 

One problem with having a lot of Cron jobs running continuously is that there isn't an easy way to tell when your jobs aren't completing successfully. You could have them notify you when they succeed, but that just leads to spam, and doesn't address the real problem. Ideally, you'd want to be notified only when your attention is required, i.e. when the job isn't completing successfully. Enter CronTrack, which was created to solve this exact problem.

## Usage

You can input jobs either individually or in groups. Given the Cron schedule string (e.g. "30 9 * * 1-5") and a time window for the job to complete in, CronTrack will calculate the next run time and send you an email/text message (configurable) if the job doesn't complete on time. This is accomplished by having you add an API call to your program being run by the job to notify CronTrack when the job completes. If CronTrack doesn't receive a notification in time, it will send you an alert. 

## Notifying CronTrack

The API call can be sent with a regular POST request, including your username and password in the POST data. E.g. with cURL:

```bash
curl https://crontrack.com/api/notifyjob/UUID_FOR_THE_JOB/ \
    -X POST \
    -d "username=YOUR_USERNAME&password=YOUR_PASSWORD"
```

## Support for Teams

You can create custom user groups which allow you to share jobs between multiple users. When you create a job or group of jobs, you can select a user group to associate it with, and all members of that group will be able to view and edit it. By default, all members of the group will also be alerted by CronTrack when jobs fail to run on time, but members can disable alerts for user groups individually.
