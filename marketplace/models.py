# marketplace/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel # Good for created_at/modified_at auto-handling
from core.models import Category # Importing from your core app
from django.conf import settings # To reference your CustomUser
from django.urls import reverse

class MarketplaceItem(TimeStampedModel):
    """
    The Master Product Table. 
    Every Mock Test, Workshop, or Note sold on the platform has an entry here.
    """
    class ItemType(models.TextChoices):
        MOCK_TEST = 'MOCK_TEST', _('Mock Test')
        WORKSHOP = 'WORKSHOP', _('Workshop')
        VIDEO_COURSE = 'VIDEO_COURSE', _('Video Course')
        NOTE = 'NOTE', _('Note')

    base_enrollment_count = models.IntegerField(
        default=0, 
        help_text="Starting number to show for social proof (e.g. 1500)"
    )

    def get_total_enrollments(self):
        # Real enrollments + Base padding
        real_count = self.enrollments.count() # Assuming related_name='enrollments' in UserEnrollment
        return self.base_enrollment_count + real_count
    
    # Translatable Fields (Will be handled by translation.py)
    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), blank=True)
    
    # Core Data
    slug = models.SlugField(unique=True, max_length=255, help_text=_("URL friendly name"))
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    thumbnail_image = models.ImageField(upload_to='thumbnails/items/', blank=True, null=True)
    price_usd = models.DecimalField(_("Price (USD)"), max_digits=10, decimal_places=2, default=0.00, help_text="Price for users outside India")
    # Relations
    categories = models.ManyToManyField(Category, related_name='items', blank=True)
    
    # Status
    is_active = models.BooleanField(default=False, help_text=_("Is this item listed for sale?"))

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('marketplace:item_detail', args=[self.slug])

class Testimonial(TimeStampedModel):
    """
    Reviews and Ratings linked to a specific Item and User.
    """
    item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE, related_name='testimonials')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    country = models.CharField(max_length=100, default="India", help_text=_("Reviewer's Country"))
    rating = models.PositiveSmallIntegerField(help_text=_("Rating from 1 to 5"))
    text = models.TextField(_("Review Text"))

    class Meta:
        # User can only review an item once
        unique_together = ('item', 'user') 

    def __str__(self):
        return f"{self.rating}/5 by {self.user.email}"

class MarketplaceCatalog(TimeStampedModel):
    """
    Represents a Bundle or a Course Catalog (e.g., 'Complete Python Bootcamp').
    Contains multiple MarketplaceItems.
    """
    # Translatable Fields
    title = models.CharField(_("Catalog Title"), max_length=255)
    description = models.TextField(_("Catalog Description"), blank=True)
    
    catalog_code = models.CharField(max_length=50, unique=True, help_text=_("Internal Code e.g. BUNDLE_2024"))
    thumbnail_image = models.ImageField(upload_to='thumbnails/catalogs/', blank=True, null=True)
    
    items = models.ManyToManyField(MarketplaceItem, through='CatalogContainsItem', related_name='catalogs')

    def __str__(self):
        return self.title

class CatalogContainsItem(models.Model):
    """
    Junction table to order items within a catalog/bundle.
    """
    catalog = models.ForeignKey(MarketplaceCatalog, on_delete=models.CASCADE)
    item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']
        unique_together = ('catalog', 'item')