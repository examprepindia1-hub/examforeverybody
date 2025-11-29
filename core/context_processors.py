from .models import Category
from django.conf import settings

def global_categories(request):
    """
    Makes 'navbar_categories' available in every HTML template.
    Fetches only top-level categories (parents).
    """
    return {
        'PAYMENTS_ACTIVE': settings.PAYMENTS_ACTIVE,
        'navbar_categories': Category.objects.filter(parent_category__isnull=True).prefetch_related('children')
    }