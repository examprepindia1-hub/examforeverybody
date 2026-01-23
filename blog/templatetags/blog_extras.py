from django import template
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
import re

register = template.Library()


# -------------------------------------------------
# Read time
# -------------------------------------------------
@register.filter
def read_time(minutes):
    """Formats read time as 'X min read'."""
    return f"{minutes} min read"


# -------------------------------------------------
# Split comma-separated tags
# -------------------------------------------------
@register.filter
def split_tags(tag_string):
    """Splits a comma-separated string into a list of tags."""
    if not tag_string:
        return []
    return [tag.strip() for tag in tag_string.split(',') if tag.strip()]


# -------------------------------------------------
# Markdown rendering
# -------------------------------------------------
@register.filter(name='markdown')
def render_markdown(text):
    """Converts markdown text to HTML."""
    import markdown
    return mark_safe(
        markdown.markdown(text or "", extensions=['extra', 'codehilite'])
    )


# -------------------------------------------------
# Marketplace item shortcode renderer
# -------------------------------------------------
@register.filter
def process_item_shortcodes(content):
    """
    Processes [[item:slug]] shortcodes and replaces them with
    cards that match the featured post HTML structure.
    """
    from marketplace.models import MarketplaceItem
    from django.urls import reverse

    pattern = r'\[\[item:([a-z0-9\-]+)\]\]'

    def replace_shortcode(match):
        slug = match.group(1)

        try:
            item = MarketplaceItem.objects.get(slug=slug, is_active=True)

            # -----------------------------------------
            # Category (top label)
            # -----------------------------------------
            if hasattr(item, 'categories') and item.categories.exists():
                category_name = item.categories.first().display_name
            else:
                category_name = item.get_item_type_display()

            # -----------------------------------------
            # Description (plain text, truncated)
            # -----------------------------------------
            raw_description = item.description or ""
            plain_description = re.sub(r'<[^>]+>', '', raw_description)
            description = Truncator(plain_description).words(20)

            # -----------------------------------------
            # Read time (optional)
            # -----------------------------------------
            read_time_value = getattr(item, 'read_time', None)
            read_time_html = ""
            if read_time_value:
                read_time_html = f"""
                <div class="text-muted small">
                    <i class="bi bi-clock me-1"></i>
                    {read_time_value} min read
                </div>
                """

            # -----------------------------------------
            # Thumbnail
            # -----------------------------------------
            if item.thumbnail_image:
                thumbnail_html = f'<img src="{item.thumbnail_image.url}" class="card-img-top object-fit-cover" alt="{item.title}" style="height: 180px;">'
            else:
                thumbnail_html = '''
                <div class="bg-secondary bg-opacity-10 d-flex align-items-center justify-content-center" style="height: 180px;">
                    <i class="bi bi-mortarboard text-secondary display-4 opacity-50"></i>
                </div>
                '''

            # -----------------------------------------
            # Badges
            # -----------------------------------------
            bestseller_badge = ''
            if getattr(item, 'is_bestseller', False):
                bestseller_badge = '<span class="badge bg-warning text-dark border-0 rounded-pill px-3 py-2 fw-semibold small shadow-sm">Bestseller</span>'
            
            free_badge = ''
            if item.price == 0:
                free_badge = '<span class="badge bg-success border-0 rounded-pill px-3 py-2 fw-semibold small shadow-sm">Free</span>'

            # -----------------------------------------
            # Duration and Students stats row
            # -----------------------------------------
            stats_html = ''
            if (item.item_type in ['MOCK_TEST', 'SCHOLARSHIP_TEST']) and hasattr(item, 'mock_test_details') and item.mock_test_details:
                duration_html = f'<div class="d-flex align-items-center gap-1"><i class="bi bi-clock"></i> {item.mock_test_details.duration_minutes}m</div>'
            else:
                duration_html = ''

            students_html = f'<div class="d-flex align-items-center gap-1"><i class="bi bi-people"></i> {int(item.total_enrollment_count):,} students</div>'

            stats_html = f'''
                                <hr class="text-muted opacity-25 my-1">
                                <div class="d-flex align-items-center gap-3 text-secondary small py-2">
                                    {duration_html}
                                    {students_html}
                                </div>
            '''

            # Student count removed from here, moved to stats_html block
            # -----------------------------------------

            # -----------------------------------------
            # Rating and Reviews
            # -----------------------------------------
            rating_html = ''
            
            # Check for annotated fields (high performance)
            avg_rating = getattr(item, 'avg_rating', None)
            review_count = getattr(item, 'review_count_annotated', None)
            
            # Fallback if not annotated (prevent crash)
            if avg_rating is None:
                reviews = item.testimonials.all()
                review_count = reviews.count()
                if review_count > 0:
                    from django.db.models import Avg
                    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
            
            if review_count and review_count > 0:
                plural = 's' if review_count != 1 else ''
                rating_html = f'''
                        <div class="d-flex align-items-center gap-1 mb-2">
                            <i class="bi bi-star-fill text-warning" style="font-size: 0.8rem;"></i>
                            <span class="fw-bold text-dark small">{avg_rating:.1f}</span>
                            <span class="text-muted small">({review_count:,} review{plural})</span>
                        </div>
                '''
            else:
                rating_html = '<div class="d-flex align-items-center gap-1 mb-2"><span class="text-muted small">New</span></div>'

            # Certificate
            # -----------------------------------------
            certificate_html = ''
            if getattr(item, 'has_certificate', False):
                certificate_html = '<span class="d-flex align-items-center gap-1"><i class="bi bi-patch-check-fill text-primary"></i> Certificate</span>'
            
            # Beginner/Level label
            level_label = '<span class="text-success">Beginner</span>'
            if (item.item_type in ['MOCK_TEST', 'SCHOLARSHIP_TEST']) and hasattr(item, 'mock_test_details') and item.mock_test_details:
                level_label = f'<span class="text-success">{item.mock_test_details.get_level_display()}</span>'

            # -----------------------------------------
            # Final card HTML
            # -----------------------------------------
            card_html = f"""
            <div class="row justify-content-center my-4">
                <div class="col-md-6 col-lg-4">
                    <div class="card h-100 border rounded-4 overflow-hidden position-relative hover-lift transition-all">
                        <!-- Thumbnail -->
                        <div class="position-relative">
                            {thumbnail_html}

                            <!-- Badges -->
                            <div class="position-absolute top-0 start-0 p-3 w-100 d-flex justify-content-between">
                                <div>{bestseller_badge}</div>
                                <div>{free_badge}</div>
                            </div>
                        </div>

                        <!-- Body -->
                        <div class="card-body p-3 d-flex flex-column gap-2">
                            <!-- Category Tag (Orange) -->
                            <div class="text-primary-orange fw-bold small text-uppercase" style="color: #fd7e14;">
                                {category_name}
                            </div>

                            <!-- Title -->
                            <h5 class="card-title fw-bold text-dark lh-sm mb-1" style="min-height: 2.5em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                                <a href="{reverse('marketplace:item_detail', args=[item.slug])}" class="text-decoration-none text-dark stretched-link">
                                    {item.title}
                                </a>
                            </h5>

                            <!-- Rating -->
                            {rating_html}

                            {stats_html}

                            <!-- Footer -->
                            <div class="d-flex align-items-center gap-3 text-secondary small fw-semibold mt-auto">
                                {level_label}
                                {certificate_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """

            return card_html

        except MarketplaceItem.DoesNotExist:
            return f"""
            <div class="alert alert-warning my-4">
                Item "{slug}" not found
            </div>
            """

    result = re.sub(pattern, replace_shortcode, content)
    return mark_safe(result)
