from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem

# ==========================================
# 1. Video Course Models
# ==========================================

class CourseAttributes(TimeStampedModel):
    """
    Specific details for a Video Course product.
    Linked One-to-One with the generic MarketplaceItem.
    """
    item = models.OneToOneField(MarketplaceItem, on_delete=models.CASCADE, primary_key=True, related_name='course_details')
    
    # Course Meta
    course_level = models.CharField(
        max_length=50, 
        choices=[('BEGINNER', 'Beginner'), ('INTERMEDIATE', 'Intermediate'), ('ADVANCED', 'Advanced')], 
        default='BEGINNER'
    )
    requirements = models.TextField(_("Requirements/Prerequisites"), blank=True)
    what_you_will_learn = models.TextField(_("What you will learn"), blank=True)
    
    def __str__(self):
        return f"Course: {self.item.title}"


class CourseModule(TimeStampedModel):
    """
    A Section or Chapter within a course (e.g. "Chapter 1: Python Basics")
    """
    course = models.ForeignKey(CourseAttributes, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(_("Module Title"), max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created']

    def __str__(self):
        return self.title


class CourseLesson(TimeStampedModel):
    """
    The actual content unit (Video + Notes).
    """
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(_("Lesson Title"), max_length=255)
    
    # Video Content
    video_url = models.URLField(
        _("Video URL"), 
        help_text=_("Embed URL for YouTube/Vimeo (e.g. https://www.youtube.com/embed/VIDEO_ID)"),
        blank=True
    )
    duration_minutes = models.PositiveIntegerField(default=0, help_text=_("Length in minutes"))
    
    # Text Content
    rich_text_content = models.TextField(_("Notes / Description"), blank=True)
    
    # Settings
    is_preview = models.BooleanField(default=False, help_text=_("Allow users to watch this without purchasing?"))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created']

    def __str__(self):
        return self.title




# ==========================================
# 2. Progress Tracking Models
# ==========================================

class UserCourseProgress(TimeStampedModel):
    """
    Tracks the overall progress of a user in a course.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(CourseAttributes, on_delete=models.CASCADE, related_name='student_progress')
    
    percent_complete = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user} - {self.course} ({self.percent_complete}%)"


class UserLessonCompletion(TimeStampedModel):
    """
    Tracks individual lesson completion.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='completed_lessons')
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='completions')
    
    # We don't strictly need a 'completed_at' field because TimeStampedModel gives us 'created'
    # But we can alias it if we want explicit naming. 'created' is sufficient.

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user} finished {self.lesson}"
