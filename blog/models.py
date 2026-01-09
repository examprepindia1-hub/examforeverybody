from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils.text import slugify

from core.models import Category

class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Hero Image for the blog
    image = models.ImageField(upload_to='blog/images/', blank=True, null=True)
    
    content = models.TextField() # You can swap this for CKEditor later for rich text
    categories = models.ManyToManyField(Category, related_name='posts', blank=True)
    # Meta fields
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New Fields for Redesign
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags (e.g. #JEE, #Physics)")
    views = models.PositiveIntegerField(default=0)

    @property
    def read_time(self):
        """Calculates read time based on 200 words per minute."""
        import math
        word_count = len(self.content.split())
        read_time_min = math.ceil(word_count / 200)
        return read_time_min if read_time_min > 0 else 1

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', args=[self.slug])