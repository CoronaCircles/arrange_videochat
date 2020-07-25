import datetime
import pytz

from django.test import TestCase
from django.core import mail
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.utils import timezone

from arrange_videochat.models import Event, MailTemplate

User = get_user_model()


class CheckSeminarsTestCase(TestCase):
    def setUp(self):
        # users
        self.host = User(email="host@example.com", username="host@example.com")
        self.host.save()
        self.participant = User(
            email="participant@example.com", username="participant@example.com"
        )
        self.participant.save()

        # events
        past_event = Event(
            host=self.host,
            start=datetime.datetime(1999, 5, 1, 20, 0, tzinfo=pytz.UTC),
            language="de",
        )
        past_event.save()
        past_event.participants.add(self.participant)

        Event(
            host=self.host, start=datetime.datetime(2222, 5, 1, 20, 0, tzinfo=pytz.UTC),
        ).save()

        # mail template
        MailTemplate(type="join", subject_template="test", body_template="test",).save()

    def test_check_mails_sent(self):
        call_command("cron")
        self.assertEqual(len(mail.outbox), 2)

    def test_not_sent_twice(self):
        call_command("cron")
        call_command("cron")
        call_command("cron")
        call_command("cron")
        self.assertEqual(len(mail.outbox), 2)


class CheckSeminarsDeletedTestCase(TestCase):
    def setUp(self):
        self.host = User(email="host@example.com", username="host@example.com")
        self.host.save()

    def test_check_old_are_deleted(self):
        past_event = Event(
            host=self.host,
            start=datetime.datetime(1999, 5, 1, 20, 0, tzinfo=pytz.UTC),
            language="de",
        )
        past_event.save()

        self.assertEqual(Event.objects.all().count(), 1)
        call_command("cron")
        self.assertEqual(Event.objects.all().count(), 0)

    def test_check_current_not_deleted(self):
        past_event = Event(host=self.host, start=timezone.now(), language="de")
        past_event.save()

        self.assertEqual(Event.objects.all().count(), 1)
        call_command("cron")
        self.assertEqual(Event.objects.all().count(), 1)
