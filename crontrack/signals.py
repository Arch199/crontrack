import pytz

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

from .models import Profile

# from https://coderwall.com/p/ktdb3g/django-signals-an-extremely-simplified-explanation-for-beginners

@receiver(post_save, sender=User)
def ensure_profile_exists(sender, **kwargs):
	if kwargs.get('created', False):
		Profile.objects.get_or_create(user=kwargs.get('instance'), timezone=pytz.utc)