from django import template

register = template.Library()

@register.filter
def read_time(minutes):
    """Formats read time as 'X min read'."""
    return f"{minutes} min read"

@register.filter
def split_tags(tag_string):
    """Splits a comma-separated string into a list of tags."""
    if not tag_string:
        return []
    return [tag.strip() for tag in tag_string.split(',') if tag.strip()]

@register.filter(name='markdown')
def render_markdown(text):
    """Converts markdown text to HTML."""
    import markdown
    from django.utils.safestring import mark_safe
    return mark_safe(markdown.markdown(text, extensions=['extra', 'codehilite']))