from modeltranslation.translator import register, TranslationOptions
from .models import MailTemplate


@register(MailTemplate)
class MailTemplateOptions(TranslationOptions):
    fields = ["subject_template", "body_template"]
