# help here: https://docs.djangoproject.com/en/2.1/howto/custom-template-tags/

from pytz import all_timezones

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Create a dropdown containing all the valid timezones
@register.simple_tag
def timezone_selector(my_timezone):
    result = '<input type="text" name="timezone" list="timezoneList" id="timezoneSelector" placeholder="Country/City" '
    result += f'value="{my_timezone}">'
    result += '<datalist id="timezoneList">'
    
    for tz in all_timezones:
        result += f'<option value="{tz}">'
        
    return mark_safe(result + '</datalist>')