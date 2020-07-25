import uuid
import datetime
import logging
import pytz

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core import mail
from django.contrib.auth import get_user_model
from django.conf import settings
from django.template import Template, Context
from django.utils import translation
from django.urls import reverse
from django.template import TemplateSyntaxError

from icalendar import Calendar, Event as IEvent

logger = logging.getLogger(__name__)
TIMEZONES = tuple(zip(pytz.common_timezones, pytz.common_timezones))
User = get_user_model()


def create_absolute_url(path: str) -> str:
    """generates an absolute url from a path using settings.ALLOWED_HOSTS"""
    domain = settings.ALLOWED_HOSTS[0]
    return "https://{domain}{path}".format(domain=domain, path=path)


class EventQuerySet(models.QuerySet):
    def upcoming(self):
        """events that are in the future"""
        return self.filter(start__gte=timezone.now())

    def to_be_mailed(self):
        """events that are to be mailed, because they start very soon"""
        return self.filter(
            mails_sent=False, start__lte=timezone.now() + datetime.timedelta(hours=1)
        )

    def to_be_deleted(self):
        """events that are to be deleted, because they are old"""
        return self.filter(start__lte=timezone.now() - datetime.timedelta(days=1))


class EventManager(models.Manager.from_queryset(EventQuerySet)):
    pass


class Event(models.Model):
    uuid = models.UUIDField(_("UUID for meeting-URL"), default=uuid.uuid4)
    created_at = models.DateTimeField(_("Creation Date"), default=timezone.now)
    start = models.DateTimeField(_("Date and Time"))
    language = models.CharField(
        _("Language"), max_length=10, choices=settings.LANGUAGES, default="en"
    )
    tzname = models.CharField(
        _("Timezone"), choices=TIMEZONES, max_length=255, default=settings.TIME_ZONE,
    )

    mails_sent = models.BooleanField(_("If e-mail has been sent"), default=False)

    host = models.ForeignKey(
        User,
        related_name="hosted_events",
        on_delete=models.CASCADE,
        verbose_name=_("Host"),
    )
    participants = models.ManyToManyField(
        User,
        related_name="events",
        verbose_name=_("Participants"),
        through="Participation",
    )

    objects = EventManager()

    @property
    def is_full(self) -> bool:
        """determines wether event is already full (4 participants, 5 including host)"""
        return self.participant_count >= 5

    @property
    def is_past(self) -> bool:
        """determines wether event is in the past"""
        return self.start < timezone.now()

    @property
    def participant_count(self) -> int:
        """current number of participants including host"""
        return self.participants.count() + 1

    @property
    def join_url(self) -> str:
        """url to join in Jitsi etc."""
        return f"https://meet.allmende.io/{self.uuid}"

    @property
    def delete_url(self) -> str:
        """url for the host to delete the event"""
        return create_absolute_url(
            reverse("arrange_videochat:delete", args=[self.uuid])
        )

    @property
    def participate_url(self) -> str:
        """url to register as participant"""
        return create_absolute_url(
            reverse("arrange_videochat:participate", args=[self.pk])
        )

    @property
    def ical(self) -> Calendar:
        """Get ical representation of event"""
        cal = Calendar()
        event = IEvent()
        event.add("summary", "Video Chat")
        event.add("dtstart", self.start)
        cal.add_component(event)
        return cal.to_ical()

    @property
    def display_tzname(self):
        """get the timezone to be used for display in e.g. mails"""
        return settings.TIME_ZONES_BY_LANG.get(self.language, settings.TIME_ZONE)

    def __str__(self) -> str:
        timezone.activate(self.tzname)
        return _("Video Chat at %(start_date)s") % {
            "start_date": self.start.strftime("%x %X")
        }

    def mail_participants(self, template_type="join"):
        """Sends mails to all participants including host with the join url

        uses the events language for the mail templates"""
        addrs = [p.email for p in self.participants.all()] + [self.host.email]

        with mail.get_connection() as connection:
            with translation.override(self.language):
                for addr in addrs:
                    email = MailTemplate.get_mail(
                        type=template_type,
                        context={"event": self},
                        to_email=addr,
                        connection=connection,
                    )
                    if email:
                        email.send(fail_silently=True)

        self.mails_sent = True
        self.save()

    class Meta:
        ordering = ("start",)
        verbose_name = _("Event")
        verbose_name_plural = _("Events")


class Participation(models.Model):
    """Saves the participation of a user on an event"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4)

    @property
    def leave_url(self):
        """get url to leave the event"""
        return create_absolute_url(reverse("arrange_videochat:leave", args=[self.uuid]))

    def __str__(self):
        return f"{self.user} {self.event}"

    class Meta:
        verbose_name = _("Participation")
        verbose_name_plural = _("Participations")


def render_template(template: str, context: dict) -> str:
    """helper to render a template str with context"""
    if template is None:
        return ""
    return Template(template).render(Context(context))


class MailTemplate(models.Model):
    type = models.CharField(
        _("Type"),
        max_length=255,
        choices=(
            ("join_confirmation", _("Join Confirmation")),
            ("host_confirmation", _("Host Confirmation")),
            ("join", _("Join")),
            ("deleted", _("Event deleted Notification")),
        ),
    )

    subject_template = models.CharField(
        _("Subject Template"),
        max_length=255,
        help_text=_(
            "Subject of the email to be sent. The Variable {{ event }} and its children {{ event.start }} etc. can be used."
        ),
    )
    body_template = models.TextField(
        _("Body Template"),
        help_text=_(
            "Body text of the email to be sent. The Variable {{ event }} and its children {{ event.start }}, {{ event.join_url }}, {{ event.delete_url }} etc. can be used. Also: {{ leave_url }} for join template only. Note that all datetimes are evaluated in the timezone of the event."
        ),
    )

    def __str__(self) -> str:
        return self.get_type_display()

    def render(
        self, context: dict, to_email: str, connection=None
    ) -> mail.EmailMessage:
        """render this email template to an email message

        try to use event.timezone"""
        from_email = settings.DEFAULT_FROM_EMAIL
        # get timezone
        try:
            tzname = context["event"].display_tzname
        except KeyError:
            tzname = None

        try:
            # render templates using timezone
            with timezone.override(tzname):
                subject = render_template(self.subject_template, context)
                body = render_template(self.body_template, context)
            return mail.EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to_email.split(","),
                connection=connection,
            )
        except TemplateSyntaxError as e:
            logger.error("Could not render mail template '%s': %s", self.type, e)
            return None

    @classmethod
    def get_mail(
        cls, type: str, context: dict, to_email: str, connection=None,
    ) -> mail.EmailMessage:
        """get template and render to email"""
        templates = cls.objects.filter(type=type)
        if not templates:
            return None

        return templates[0].render(
            context=context, to_email=to_email, connection=connection
        )

    class Meta:
        ordering = ("type",)
        verbose_name = _("MailTemplate")
        verbose_name_plural = _("MailTemplates")
