# marketplace/views.py

from django.views.generic import DetailView, ListView
from django.db.models import Avg
from .models import MarketplaceItem, Testimonial
from enrollments.models import UserEnrollment
from billing.models import Order  # <--- NEW IMPORT

class ItemListView(ListView):
    model = MarketplaceItem
    template_name = 'marketplace/item_list.html'
    context_object_name = 'items'

class ItemDetailView(DetailView):
    model = MarketplaceItem
    template_name = 'marketplace/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return MarketplaceItem.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        user = self.request.user
        
        # 1. Reviews & Ratings
        reviews = Testimonial.objects.filter(item=item).order_by('-created')
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        context['reviews'] = reviews
        context['avg_rating'] = avg_rating if avg_rating else 0
        context['review_count'] = reviews.count()

        # 2. Enrollment Check
        is_enrolled = False
        latest_order_status = None # <--- NEW VARIABLE

        if user.is_authenticated:
            is_enrolled = UserEnrollment.objects.filter(user=user, item=item).exists()
            
            # 3. IF NOT ENROLLED: Check for Pending/Failed orders
            if not is_enrolled:
                # Get the most recent order for THIS item by this user
                last_order = Order.objects.filter(
                    user=user, 
                    items__item=item
                ).order_by('-created').first()

                if last_order:
                    latest_order_status = last_order.status

        context['is_enrolled'] = is_enrolled
        context['latest_order_status'] = latest_order_status # <--- Pass to template
        
        return context