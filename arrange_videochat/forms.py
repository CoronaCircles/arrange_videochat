from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.utils import formats
from django.conf import settings

from bootstrap_datepicker_plus import DateTimePickerInput

from .models import Event


class Host(forms.ModelForm):
    email = forms.EmailField(label=_("E-mail address"))

    def full_clean(self):
        # activate timezone to make dateparsing aware of it
        if "tzname" in self.data:
            tzname = self.data["tzname"]
            timezone.activate(tzname)

        super().full_clean()

    def clean_start(self):
        start = self.cleaned_data["start"]
        if start < timezone.now():
            raise forms.ValidationError(_("Has to be in the future"))
        return start

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # default to current language
        self.fields["language"].initial = get_language()

        # default to current timezone
        self.fields["tzname"].initial = settings.TIME_ZONES_BY_LANG.get(
            get_language(), settings.TIME_ZONE
        )

        # localize datepicker
        locale_formats = formats.get_format("DATETIME_INPUT_FORMATS")
        self.fields["start"].widget = DateTimePickerInput(
            format=locale_formats[2],  # format without seconds
            options={"sideBySide": True, "locale": get_language()},
        )

    class Meta:
        fields = ["start", "tzname", "language", "email"]
        model = Event


class Participate(forms.Form):
    email = forms.EmailField(label=_("E-mail address"))

    class Meta:
        fields = ["email"]
