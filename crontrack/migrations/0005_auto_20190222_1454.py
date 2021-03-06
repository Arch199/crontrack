# Generated by Django 2.1.7 on 2019-02-22 04:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crontrack', '0004_job_last_failed'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField()),
            ],
        ),
        migrations.AlterField(
            model_name='job',
            name='time_window',
            field=models.PositiveIntegerField(default=0, verbose_name='time window (minutes)'),
        ),
        migrations.AddField(
            model_name='jobevent',
            name='job',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='crontrack.Job'),
        ),
    ]
