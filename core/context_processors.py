from .models import Category

def global_categories(request):
    """
    Makes 'navbar_categories' available in every HTML template.
    Fetches only top-level categories (parents).
    """
    return {
        'navbar_categories': Category.objects.filter(parent_category__isnull=True).prefetch_related('children')
    }