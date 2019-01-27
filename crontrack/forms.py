# TODO: move more forms into this implementation (?)

from django import forms
from django.contrib.auth.forms import UserCreationForm
from timezone_field import TimeZoneFormField
from phonenumber_field.formfields import PhoneNumberField

from .models import User

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')

class ProfileForm(forms.Form):
    timezone = TimeZoneFormField(label='Timezone', initial='UTC')
    alert_method = forms.ChoiceField(
        label='Alert method',
        widget=forms.RadioSelect,
        choices=User.ALERT_METHOD_CHOICES,
    )
    email = forms.EmailField(label='Email address', required=False)
    full_phone = PhoneNumberField(label='Phone number', required=False)
    alert_buffer = forms.IntegerField()