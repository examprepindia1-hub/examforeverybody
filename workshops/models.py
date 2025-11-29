# workshops/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem

class WorkshopAttributes(TimeStampedModel):
    """
    Defines a Workshop Product (e.g., "Python Masterclass").
    Linked One-to-One with the generic MarketplaceItem.
    """
    item = models.OneToOneField(MarketplaceItem, on_delete=models.CASCADE, primary_key=True, related_name='workshop_details')
    
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='taught_workshops')
    
    # Translatable content specific to workshops
    description_long = models.TextField(_("Detailed Agenda"), help_text=_("Full schedule or curriculum details"))
    prerequisites = models.TextField(_("Prerequisites"), blank=True)
    
    total_duration_hours = models.DecimalField(max_digits=4, decimal_places=2, help_text=_("Approximate total duration"))

    def __str__(self):
        return f"Workshop: {self.item.title}"

class WorkshopSession(TimeStampedModel):
    """
    A specific occurrence of a workshop.
    e.g., The "Oct 25th, 10 AM" session of the "Python Masterclass".
    """
    workshop = models.ForeignKey(WorkshopAttributes, on_delete=models.CASCADE, related_name='sessions')
    
    start_time = models.DateTimeField(_("Start Time"), db_index=True)
    end_time = models.DateTimeField(_("End Time"))
    
    # Capacity Management
    max_capacity = models.PositiveIntegerField(default=50)
    current_enrolled_count = models.PositiveIntegerField(default=0, help_text=_("Auto-updated by signals/logic"))
    
    # Delivery
    meeting_link = models.URLField(_("Zoom/Meet Link"), blank=True)
    recording_link = models.URLField(_("Recording URL"), blank=True, help_text=_("Available after session ends"))

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.workshop.item.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

class WorkshopAttendee(TimeStampedModel):
    """
    Junction table: Which user is attending which specific session?
    """
    session = models.ForeignKey(WorkshopSession, on_delete=models.CASCADE, related_name='attendees')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workshop_bookings')
    
    attended = models.BooleanField(default=False, help_text=_("Did the user actually show up?"))
    feedback_submitted = models.BooleanField(default=False)

    class Meta:
        # A user can't book the same session twice
        unique_together = ('session', 'user')

    def __str__(self):
        return f"{self.user} -> {self.session}"