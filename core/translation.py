# core/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import Category

@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('display_name',) # These fields will be translated