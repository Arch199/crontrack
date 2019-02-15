import os

from django.urls import reverse_lazy

# Production settings
# for reference: https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

DEBUG = False
JOB_MONITOR_ON = True  # Whether to run the job alert monitor

SITE_PROTOCOL = 'https'
SITE_DOMAIN = 'crontrack.com'
ALLOWED_HOSTS = [SITE_DOMAIN, f'www.{SITE_DOMAIN}']
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUTH_USER_MODEL = 'crontrack.User'


# Login / logout

LOGIN_URL = reverse_lazy('crontrack:login')
LOGIN_REDIRECT_URL = reverse_lazy('crontrack:view_jobs')
LOGOUT_REDIRECT_URL = reverse_lazy('crontrack:index')


# Email

DEFAULT_FROM_EMAIL = 'crontrack@ostinc.net'


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'crontrack.views': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
        'crontrack.background': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
    },
    'formatters': {
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
}


# Application definition

INSTALLED_APPS = [
    'anymail',                       # https://github.com/anymail/django-anymail
    'phonenumber_field',               # https://github.com/stefanfoulis/django-phonenumber-field
    'timezone_field',                 # https://github.com/mfogel/django-timezone-field
    'crontrack.apps.CronTrackConfig',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'crontrack_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crontrack_site.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'crontrack', 'staticfiles')


# Import all local settings

from .local_settings import *