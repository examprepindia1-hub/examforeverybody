# mocktests/models.py

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from marketplace.models import MarketplaceItem

# ==========================================
# 1. Content Structure
# ==========================================

class MockTestAttributes(TimeStampedModel):
    """
    Specific details for a Mock Test product.
    Linked One-to-One with the generic MarketplaceItem.
    """
    item = models.OneToOneField(MarketplaceItem, on_delete=models.CASCADE, primary_key=True, related_name='mock_test_details')
    
    # Difficulty & Time
    level = models.CharField(max_length=50, choices=[('BEGINNER', 'Beginner'), ('INTERMEDIATE', 'Intermediate'), ('ADVANCED', 'Advanced')], default='BEGINNER')
    duration_minutes = models.PositiveIntegerField(help_text=_("Total time allowed in minutes"))
    
    # Scoring Config
    pass_percentage = models.PositiveIntegerField(default=50, help_text=_("Minimum % to pass"))
    has_negative_marking = models.BooleanField(default=False)
    negative_marking_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text=_("e.g. 0.25 for 25% deduction"))
    
    # Leaderboard Logic
    ranking_weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text=_("Multiplier for the global ranking (e.g., 1.5 for final exams)"))

    def __str__(self):
        return f"Details for: {self.item.title}"

class TestSection(models.Model):
    """
    Tests are often divided into sections (e.g., 'Verbal Ability', 'Logic').
    """
    test = models.ForeignKey(MockTestAttributes, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(_("Section Title"), max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.title} ({self.test.item.title})"
    

class ComprehensionPassage(models.Model):
    """
    For SAT/GRE/IELTS Reading sections.
    One passage is linked to multiple questions.
    """
    # We link it to a section (e.g. "Verbal Reasoning")
    section = models.ForeignKey(TestSection, on_delete=models.CASCADE, related_name='passages')
    
    content = models.TextField(_("Passage Text"))
    image = models.ImageField(upload_to='passages/images/', null=True, blank=True)
    
    # Translatable
    # Note: In translation.py, register 'content'
    
    def __str__(self):
        return f"Passage: {self.content[:50]}..."

class TestQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MCQ = 'MCQ', _('Multiple Choice')
        NUMERIC = 'NUMERIC', _('Numeric Input')
        ESSAY = 'ESSAY', _('Essay / Long Answer') # Added for IELTS/TOEFL/CBSE

    section = models.ForeignKey(TestSection, on_delete=models.CASCADE, related_name='questions')
    
    # NEW: Link to a passage (Optional, because not all questions have passages)
    passage = models.ForeignKey(ComprehensionPassage, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    question_text = models.TextField(_("Question Text"))
    explanation = models.TextField(_("Explanation"), blank=True)
    
    # NEW: Media Support for NEET/IELTS
    question_image = models.ImageField(upload_to='questions/images/', null=True, blank=True, help_text=_("Diagrams for JEE/NEET"))
    audio_clip = models.FileField(upload_to='questions/audio/', null=True, blank=True, help_text=_("For IELTS/TOEFL Listening"))

    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MCQ)
    marks = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."

class QuestionOption(models.Model):
    """
    Options for MCQ questions.
    """
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(_("Option Text"), max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.option_text

# ==========================================
# 2. User Progress & Results
# ==========================================

class UserTestAttempt(TimeStampedModel):
    """
    Tracks a specific attempt by a user on a test.
    """
    class Status(models.TextChoices):
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        SUBMITTED = 'SUBMITTED', _('Submitted')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(MockTestAttributes, on_delete=models.CASCADE, related_name='attempts')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    
    # Results
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(default=False)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.test.item.title}"

class UserAnswer(TimeStampedModel):
    attempt = models.ForeignKey(UserTestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    
    # 1. MCQ Answer
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True)
    
    # 2. Numeric Answer (JEE)
    numeric_answer = models.CharField(max_length=255, null=True, blank=True)
    
    # 3. NEW: Essay/Subjective Answer (IELTS/CBSE)
    text_answer = models.TextField(null=True, blank=True, help_text=_("For Essay or Subjective questions"))
    
    is_correct = models.BooleanField(default=False)
    
    # Score awarded for this specific answer (useful for partial marking in CBSE)
    score_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('attempt', 'question')

# ==========================================
# 3. Global Ranking Engine
# ==========================================

class UserRankMetric(TimeStampedModel):
    """
    Denormalized table for the Leaderboard.
    Populated by a background task (Cron Job), not real-time.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rank_metrics')
    
    total_xp = models.IntegerField(default=0, db_index=True) # Indexed for fast sorting
    tests_taken_count = models.PositiveIntegerField(default=0)
    avg_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return f"{self.user} - XP: {self.total_xp}"
    
class QuestionReport(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE)
    report_text = models.TextField()
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Report by {self.user} on Q{self.question.id}"