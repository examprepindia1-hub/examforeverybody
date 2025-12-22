# billing/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem

class Order(TimeStampedModel):
    """
    Represents a Shopping Cart Checkout.
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PAID = 'PAID', _('Paid')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    payer_upi_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Customer's VPA used for verification"
    )
    qr_code = models.ImageField(upload_to='upi_qr/', blank=True, null=True)
    # Payment Gateway Info
    payment_method = models.CharField(max_length=50, default='STRIPE', help_text="STRIPE, PAYPAL, etc.")
    transaction_id = models.CharField(max_length=100, blank=True, help_text="ID from Stripe/PayPal")

    def __str__(self):
        return f"Order #{self.id} - {self.user} ({self.status})"

class OrderItem(TimeStampedModel):
    """
    Individual items inside an Order.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(MarketplaceItem, on_delete=models.SET_NULL, null=True)
    
    # We store the price AT THE MOMENT of purchase (in case prices change later)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item.title} in Order #{self.order.id}"