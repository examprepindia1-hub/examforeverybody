# marketplace/views.py
from django.views.generic import DetailView
from django.db.models import Avg 
from .models import MarketplaceItem, Testimonial

# --- Add this import ---
from enrollments.models import UserEnrollment
# -----------------------

class ItemDetailView(DetailView):
    model = MarketplaceItem
    template_name = 'marketplace/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        # Only allow viewing active items
        return MarketplaceItem.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        
        # 1. Fetch reviews
        reviews = Testimonial.objects.filter(item=item).order_by('-created')
        
        # 2. Calculate average rating
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

        # 3. --- CHECK ENROLLMENT STATUS ---
        is_enrolled = False
        if self.request.user.is_authenticated:
            is_enrolled = UserEnrollment.objects.filter(
                user=self.request.user, 
                item=item
            ).exists()
        # ----------------------------------

        # Add to context
        context['reviews'] = reviews
        context['avg_rating'] = avg_rating if avg_rating else 0
        context['review_count'] = reviews.count()
        
        # Pass this new flag to the template so the button changes!
        context['is_enrolled'] = is_enrolled
        
        return context