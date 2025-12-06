import re
import markdown
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from marketplace.models import MarketplaceItem

register = template.Library()

@register.filter
def markdown_with_cards(text):
    """
    1. Converts Markdown text to HTML.
    2. Replaces [[item:slug]] with a properly styled Item Card.
    """
    if not text:
        return ""

    # 1. Convert Markdown to HTML (handles bold, lists, headers)
    html_content = markdown.markdown(text, extensions=['nl2br', 'extra'])

    # 2. Regex to find [[item:some-slug]]
    pattern = r'\[\[item:([\w-]+)\]\]'

    def replacer(match):
        slug = match.group(1)
        try:
            item = MarketplaceItem.objects.get(slug=slug, is_active=True)
            
            # Render the existing card template
            card_html = render_to_string('includes/item_card.html', {'item': item})
            
            # --- WIDTH FIX ---
            # The original card has "col-12 col-md-6..." classes which ruin the blog layout.
            # We strip those outer column classes using simple string manipulation 
            # OR wrap it in a div that overrides grid behavior.
            
            # Hacky but effective: Replace the outer column div with a neutral div
            # (Assuming your item_card.html starts with <div class="col-...)
            if card_html.strip().startswith('<div class="col'):
                card_html = re.sub(r'^<div class="[^"]+">', '<div class="card-wrapper">', card_html, count=1)

            return f"""
            <div class="my-5 p-4 bg-light rounded-3 border d-flex justify-content-center">
                <div style="max-width: 350px; width: 100%;">
                    {card_html}
                </div>
            </div>
            """
        except MarketplaceItem.DoesNotExist:
            return f"""
            <div class="alert alert-warning small my-3">
                <i class="bi bi-exclamation-triangle"></i> Item '{slug}' not found.
            </div>
            """

    # 3. Inject Cards into the HTML
    processed_html = re.sub(pattern, replacer, html_content)
    
    return mark_safe(processed_html)