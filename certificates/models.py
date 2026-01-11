from django.db import models
from django.conf import settings
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem
import uuid

class Certificate(TimeStampedModel):
    """
    Represents a verified certificate issued to a user.
    """
    certificate_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    item = models.ForeignKey(MarketplaceItem, on_delete=models.CASCADE, related_name='issued_certificates')
    
    # Optional: We can store the generated PDF to avoid re-generating it every time
    # For now, we'll generate on the fly to save storage, but keeping the field structure in mind
    # pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)

    class Meta:
        unique_together = ('user', 'item')
        ordering = ['-created']

    def __str__(self):
        return f"Certificate {self.certificate_id} for {self.user}"

