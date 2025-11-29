# mocktests/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import TestSection, TestQuestion, QuestionOption

@register(TestSection)
class TestSectionTranslationOptions(TranslationOptions):
    fields = ('title',)

@register(TestQuestion)
class TestQuestionTranslationOptions(TranslationOptions):
    fields = ('question_text', 'explanation')

@register(QuestionOption)
class QuestionOptionTranslationOptions(TranslationOptions):
    fields = ('option_text',)