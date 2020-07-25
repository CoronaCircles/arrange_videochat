from django.views.generic import (
    ListView,
    CreateView,
    DeleteView,
    FormView,
    DetailView,
)
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import translation

from .models import Event, MailTemplate, Participation
from .forms import Host, Participate


User = get_user_model()


class EventList(ListView):
    """Listing of upcoming events"""

    context_object_name = "events"
    template_name = "arrange_videochat/list.html"
    queryset = Event.objects.upcoming().prefetch_related("participants")


class EventHost(CreateView):
    """Create/Host a new event"""

    model = Event
    template_name = "arrange_videochat/host.html"
    form_class = Host

    def get_success_url(self):
        return reverse("arrange_videochat:hosted", args=[self.object.pk])

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user, _ = User.objects.get_or_create(email=email, username=email)
        event = form.instance
        event.host = user
        event.save()

        # send mail
        with translation.override(event.language):
            mail = MailTemplate.get_mail(
                type="host_confirmation", context={"event": event}, to_email=email,
            )
            if mail:
                mail.attach(
                    filename="event.ical", content=event.ical, mimetype="text/calendar"
                )
                mail.send(fail_silently=True)

        return super().form_valid(form)


class EventHostConfirmation(DetailView):
    """Show a confirmation message for having hosted an event"""

    model = Event
    template_name = "arrange_videochat/hosted.html"
    context_object_name = "event"


class EventDeleteView(DeleteView):
    """Allows the host to delete the event."""

    model = Event
    success_url = "/"
    context_object_name = "event"

    def get_object(self):
        return get_object_or_404(Event, uuid=self.kwargs["uuid"])

    def delete(self, request, *args, **kwargs):
        # mail participants
        event = self.get_object()
        event.mail_participants(template_type="deleted")

        return super().delete(request, *args, **kwargs)


class EventJoin(FormView):
    """Allows to join the event

    Asks user for mail. Sends mail with details for event"""

    template_name = "arrange_videochat/participate.html"
    form_class = Participate

    def get_success_url(self):
        return reverse("arrange_videochat:participated", args=[self.get_object().pk])

    def get_object(self):
        return get_object_or_404(Event, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["event"] = self.get_object()
        return data

    def form_valid(self, form):
        event = self.get_object()

        if event.is_full or event.is_past:
            return render(
                self.request,
                "arrange_videochat/full_or_past.html",
                {"event": event},
                status=400,
            )

        email = form.cleaned_data["email"]
        user, _ = User.objects.get_or_create(email=email, username=email)
        participation, _ = Participation.objects.get_or_create(event=event, user=user)

        # send mail
        with translation.override(event.language):
            mail = MailTemplate.get_mail(
                type="join_confirmation",
                context={"event": event, "leave_url": participation.leave_url},
                to_email=email,
            )
            if mail:
                mail.attach(
                    filename="event.ical", content=event.ical, mimetype="text/calendar"
                )
                mail.send(fail_silently=True)

        return super().form_valid(form)


class EventJoinConfirmation(DetailView):
    """Show a confirmation message for having joined an event"""

    model = Event
    template_name = "arrange_videochat/participated.html"
    context_object_name = "event"


class EventLeaveView(DeleteView):
    """Allows a participant to leave an event, freeing their seat"""

    model = Participation
    success_url = "/"
    context_object_name = "participation"

    def get_object(self):
        return get_object_or_404(Participation, uuid=self.kwargs["uuid"])
