from django.urls import path, include, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views

app_name = 'crontrack'
urlpatterns = [
    path('', views.index, name='index'),
    path('viewjobs/', views.view_jobs, name='view_jobs'),
    path('addjob/', views.add_job, name='add_job'),
    path('editgroup/', views.edit_group, name='edit_group'),
    path('deletegroup/', views.delete_group, name='delete_group'),
    path('deletejob/', views.delete_job, name='delete_job'),
    
    path('teams/', views.user_groups, name='user_groups'),
    
    path('p/<uuid:id>/', views.notify_job, name='notify_job'),
    
    path('accounts/profile/', views.profile, name='profile'),
    path('accounts/register/', views.RegisterView.as_view(), name='register'),
    path('accounts/delete/', views.delete_account, name='delete_account'),
    
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'accounts/password_change/',
        auth_views.PasswordChangeView.as_view(success_url=reverse_lazy('crontrack:password_change_done')),
        name='password_change',
    ),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path(
        'accounts/password_reset/',
        auth_views.PasswordResetView.as_view(success_url=reverse_lazy('crontrack:password_reset_done')),
        name='password_reset',
    ),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path(
        'accounts/reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(success_url=reverse_lazy('crontrack:password_reset_complete')),
        name='password_reset_confirm',
    ),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    #path('accounts/', include('django.contrib.auth.urls')),
]