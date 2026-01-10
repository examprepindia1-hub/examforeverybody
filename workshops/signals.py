from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import F
from enrollments.models import UserEnrollment
from .models import WorkshopAttributes, WorkshopSession

@receiver(post_save, sender=UserEnrollment)
def increment_workshop_enrollment(sender, instance, created, **kwargs):
    """
    When a user enrolls in a Workshop item, increment the count on its Sessions.
    NOTE: Currently simplistic - assumes enrolling in the ITEM enrolls in ALL sessions.
    """
    if created and instance.item.item_type == 'WORKSHOP':
        # Safely increment using F expression to avoid race conditions
        WorkshopSession.objects.filter(workshop__item=instance.item).update(
            current_enrolled_count=F('current_enrolled_count') + 1
        )

@receiver(post_delete, sender=UserEnrollment)
def decrement_workshop_enrollment(sender, instance, **kwargs):
    """
    If enrollment is deleted (refunded), decrement.
    """
    if instance.item.item_type == 'WORKSHOP':
        WorkshopSession.objects.filter(workshop__item=instance.item).update(
            current_enrolled_count=F('current_enrolled_count') - 1
        )
