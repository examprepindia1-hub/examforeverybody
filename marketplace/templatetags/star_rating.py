from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def render_stars(value):
    """
    Converts a number (e.g. 3.7) into Bootstrap icon HTML.
    Logic: Rounds to nearest 0.5.
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = 0

    # 1. Round to nearest 0.5 (e.g., 3.7 -> 3.5, 3.8 -> 4.0)
    rating = round(value * 2) / 2
    
    full_stars = int(rating)
    has_half_star = (rating - full_stars) == 0.5
    empty_stars = 5 - full_stars - (1 if has_half_star else 0)

    html = ""
    
    # 2. Add Full Stars
    html += '<i class="bi bi-star-fill"></i>' * full_stars
    
    # 3. Add Half Star
    if has_half_star:
        html += '<i class="bi bi-star-half"></i>'
        
    # 4. Add Empty Stars
    html += '<i class="bi bi-star"></i>' * empty_stars
    
    return mark_safe(html)