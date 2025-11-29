# workshops/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import WorkshopAttributes

@register(WorkshopAttributes)
class WorkshopAttributesTranslationOptions(TranslationOptions):
    fields = ('description_long', 'prerequisites')