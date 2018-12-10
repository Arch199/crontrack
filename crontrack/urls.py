from django.urls import path

from . import views

app_name = 'crontrack'
urlpatterns = [
	path('', views.index, name='index'),
	path('addjob', views.add_job, name='add_job'),
	#path('addjobresult', views.add_job_result, name='add_job_result'),
]