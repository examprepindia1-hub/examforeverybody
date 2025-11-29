# marketplace/views.py
from django.views.generic import DetailView
from django.db.models import Avg # Import Avg to calculate average rating
from .models import MarketplaceItem, Testimonial


class ItemDetailView(DetailView):
    model = MarketplaceItem
    template_name = 'marketplace/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        # Only allow viewing active items
        return MarketplaceItem.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        # Get default context (which contains 'item')
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        
        # Fetch reviews for THIS specific item, newest first
        reviews = Testimonial.objects.filter(item=item).order_by('-created')
        
        # Calculate average rating
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

        # Add to context so the template can use them
        context['reviews'] = reviews
        context['avg_rating'] = avg_rating if avg_rating else 0
        context['review_count'] = reviews.count()
        
        return context