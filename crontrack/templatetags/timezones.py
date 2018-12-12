# help here: https://docs.djangoproject.com/en/2.1/howto/custom-template-tags/

from pytz import all_timezones
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def timezone_select(prefill):
	my_timezone = dict(prefill).get('timezone', 'UTC')
	result = '<input name="timezone" list="timezoneList">'
	result += '<datalist id="timezoneList">'
	
	for tz in all_timezones:
		result += f'<option value="{tz}">'
		
	return mark_safe(result + '</datalist>')