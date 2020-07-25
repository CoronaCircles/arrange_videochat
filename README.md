# Arrange Videochat

Django app to arrange a meeting for a video chat for a group of people.

## Functionality
It show a public list of upcoming video chat events, allows to add a new event to the list and to join an event by stating your mail address.
Registered participants for an event will get the unique video chat url to join the video chat.

Automatic emails can be set up by configuring mail templates in the admin, allowing to confirm the creation and participation in an event
or to remind registered participants of the start of an event.

Participants can leave an event by using a secret url sent to them by mail.
Creators of events can delete event by using a secret url sent to them by mail.

The Ui and mails are fully internationalized.

## Installation
1. Install the package
    ```
    pip install arrange_videochat
    ```


2. Add arrange_videochat and its dependecies to your settings installed apps:
    ```
    INSTALLED_APPS = [
        ...
        "crispy_forms",
        "bootstrap_datepicker_plus",
        "arrange_videochat",
        ...
    ]
    ```


3. Include the arrange_videochat URLconf in your project urls.py like this:
    ```
    path('chat/', include('arrange_videochat.urls')),
    ```


4. You need to migrate after installing:
    ```
    python manage.py migrate
    ```


5. Create a base template in `templates/base.html`. All templates from arrange_videochat inherit from `base.html`.

## Configuration
```
TIME_ZONES_BY_LANG = {"de": "Europe/Berlin", "en": "UTC"}
```

```
DEFAULT_FROM_EMAIL
```

## Dependencies
crispy_forms
bootstrap_datepicker_plus
arrange_videochat
django-ckeditor
icalendar
django-modeltranslation

## Cron job
Setup a cron job that runs the following command to delete old events and to remind participants of events that start soon:
```
python manage.py cron
```