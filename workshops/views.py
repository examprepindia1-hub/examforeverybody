from django.views.generic import DetailView
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from .models import WorkshopAttributes

class WorkshopAccessView(LoginRequiredMixin, DetailView):
    model = MarketplaceItem
    template_name = 'workshops/workshop_access.html'
    context_object_name = 'item'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        # 1. Get the item
        self.object = self.get_object()
        
        # 2. Check Enrollment
        is_enrolled = UserEnrollment.objects.filter(
            user=request.user, 
            item=self.object,
            is_active=True
        ).exists()
        
        if not is_enrolled:
            messages.error(request, "You must enroll in this workshop to access the details.")
            return redirect('marketplace:item_detail', slug=self.object.slug)
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get Workshop Attributes
        try:
            workshop = self.object.workshop_details
        except WorkshopAttributes.DoesNotExist:
            workshop = None
            
        context['workshop'] = workshop
        return context
