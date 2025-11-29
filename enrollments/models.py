# enrollments/models.py

from django.db import models
from django.conf import settings
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem
from billing.models import Order

class UserEnrollment(TimeStampedModel):
    """
    The 'Ticket'. If a record exists here, the user owns the content.
    Points to the generic MarketplaceItem, so it works for Tests, Videos, and Workshops.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE, related_name='enrollments')
    
    # Optional: Link to the order that created this enrollment
    source_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        # Prevent double enrollment
        unique_together = ('user', 'item')

    def __str__(self):
        return f"{self.user} -> {self.item}"