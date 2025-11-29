# marketplace/translation.py
from modeltranslation.translator import register, TranslationOptions
from .models import MarketplaceItem, MarketplaceCatalog

@register(MarketplaceItem)
class MarketplaceItemTranslationOptions(TranslationOptions):
    fields = ('title', 'description')

@register(MarketplaceCatalog)
class MarketplaceCatalogTranslationOptions(TranslationOptions):
    fields = ('title', 'description')