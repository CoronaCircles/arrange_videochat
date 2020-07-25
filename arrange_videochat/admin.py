from django.contrib import admin

from modeltranslation.admin import TranslationAdmin

from .models import Event, MailTemplate


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("uuid", "start", "language", "host")


@admin.register(MailTemplate)
class MailTemplateAdmin(TranslationAdmin):
    list_display = ("type",)
