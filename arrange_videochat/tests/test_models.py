import datetime
import pytz

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import translation
from django.urls import reverse

from arrange_videochat.models import Event, MailTemplate

User = get_user_model()


class EventTestCase(TestCase):
    def setUp(self):
        self.host = User(email="host@example.com", username="host@example.com")
        self.host.save()

        self.event = Event(
            host=self.host, start=datetime.datetime(2020, 5, 1, 20, 0, tzinfo=pytz.UTC)
        )
        self.event.save()

    def test_is_past(self):
        event = Event(
            host=self.host, start=datetime.datetime(1999, 5, 1, 20, 0, tzinfo=pytz.UTC)
        )
        self.assertTrue(event.is_past)

    def test_is_full(self):
        self.assertFalse(self.event.is_full)
        # create 6 participants
        for i in range(1, 7):
            email = f"test{i}@example.com"
            user = User(email=email, username=email)
            user.save()
            self.event.participants.add(user)
        self.event.save()
        self.assertTrue(self.event.is_full)

    def test_participate_url(self):
        self.assertIn(
            reverse("arrange_videochat:participate", args=[self.event.pk]),
            self.event.participate_url,
        )

    def test_ical(self):
        self.assertEqual(
            self.event.ical,
            b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Video Chat Event\r\nDTSTART;VALUE=DATE-TIME:20200501T200000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n",
        )

    def test_mail_participants(self):
        event = Event(
            host=self.host,
            start=datetime.datetime(2020, 5, 1, 20, 0, tzinfo=pytz.UTC),
            language="de",
            tzname="US/Pacific",
        )
        event.save()
        MailTemplate(
            type="join",
            subject_template_en="english",
            body_template_en="english",
            subject_template_de="deutsch",
            body_template_de="{{ event.start }}",
        ).save()
        event.mail_participants()

        # mail is sent
        self.assertEqual(len(mail.outbox), 1)
        # mail is on right language
        self.assertEqual(mail.outbox[0].subject, "deutsch")
        # mail is in right timezone (20:00 UTC is 22:00 CEST)
        self.assertEqual(mail.outbox[0].body, "1. Mai 2020 22:00")


class EventQuerySetTestCase(TestCase):
    def test_upcoming(self):
        self.host = User(email="host@example.com", username="host@example.com")
        self.host.save()
        Event(
            host=self.host, start=datetime.datetime(1999, 5, 1, 20, 0, tzinfo=pytz.UTC)
        ).save()
        Event(
            host=self.host, start=datetime.datetime(2222, 5, 1, 20, 0, tzinfo=pytz.UTC)
        ).save()
        self.assertEqual(Event.objects.upcoming().count(), 1)


class MailTemplateTestCase(TestCase):
    def test_render(self):
        self.template = MailTemplate(
            type="join_confirmation",
            subject_template="Event beigetreten",
            body_template="{{ testvariable }}",
        )
        self.template.save()
        email = self.template.render(
            {"testvariable": "This is a test"}, "max@example.com"
        )
        self.assertEqual(email.body, "This is a test")
        self.assertEqual(email.subject, "Event beigetreten")
        self.assertEqual(email.to, ["max@example.com"])

    def test_get_mail(self):
        self.template = MailTemplate(
            type="join_confirmation",
            subject_template="Event beigetreten",
            body_template="{{ testvariable }}",
        )
        self.template.save()
        email = MailTemplate.get_mail(
            "join_confirmation", {"testvariable": "This is a test"}, "max@example.com",
        )
        self.assertEqual(email.subject, "Event beigetreten")

    def test_get_right_language(self):
        MailTemplate(
            type="join_confirmation",
            subject_template_en="english",
            body_template_en="english",
            subject_template_de="deutsch",
            body_template_de="deutsch",
        ).save()

        translation.activate("de")
        email = MailTemplate.get_mail("join_confirmation", {}, "max@example.com",)
        self.assertEqual(email.subject, "deutsch")

        translation.activate("en")
        email = MailTemplate.get_mail("join_confirmation", {}, "max@example.com",)
        self.assertEqual(email.subject, "english")
