# TODO: move more forms into this implementation (?)

from django import forms
from timezone_field import TimeZoneFormField

from .models import Profile

class ProfileForm(forms.Form):
	timezone = TimeZoneFormField(label='Timezone', initial='UTC')
	alert_method = forms.ChoiceField(
		label='Alert method',
		widget=forms.RadioSelect,
		choices=Profile.ALERT_METHOD_CHOICES,
	)
	email = forms.EmailField(label='Email address', required=False)
	#TODO: add phone number field