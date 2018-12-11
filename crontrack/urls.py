from django.urls import path, include

from . import views

app_name = 'crontrack'
urlpatterns = [
	path('', views.index, name='index'),
	path('viewjobs', views.view_jobs, name='view_jobs'),
	path('addjob', views.add_job, name='add_job'),
	
	path('accounts/', include('django.contrib.auth.urls')),
	path('accounts/profile', views.profile, name='profile'),
	path('accounts/register', views.Register.as_view(), name='register'),
]