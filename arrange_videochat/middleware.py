import pytz

from django.utils import timezone
from django.conf import settings


class TimezoneMiddleware:
    """Sets the timezone depending on the request locale"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_code = request.LANGUAGE_CODE
        tzname = settings.TIME_ZONES_BY_LANG.get(language_code, settings.TIME_ZONE)
        timezone.activate(pytz.timezone(tzname))
        return self.get_response(request)
