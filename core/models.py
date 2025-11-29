from django.db import models
# Import for i18n: Assuming you'll use django-modeltranslation or similar for display_name
from model_utils.models import TimeStampedModel 

# 1. Categories Table (categories)
class Category(TimeStampedModel):
    value = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Internal Code"
    )
    # This field will be translated (e.g., using django-modeltranslation)
    display_name = models.CharField(
        max_length=100, 
        verbose_name="Display Name"
    ) 
    
    # Self-Referential FK for hierarchy (e.g., Math -> Calculus)
    parent_category = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children'
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_name']

    def __str__(self):
        return self.display_name