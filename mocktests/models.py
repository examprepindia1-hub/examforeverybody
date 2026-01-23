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
    EXAM_TYPES=[
        ('GENERAL', 'General Mock Test'),
        ('SAT_ADAPTIVE', 'Digital SAT (Adaptive)'),
        ('SAT_NON_ADAPTIVE', 'Digital SAT (Non-Adaptive)'),
        ('IELTS', 'IELTS Academic/General'),
        ('JEE_MAINS', 'JEE Mains'),
        ('JEE_ADVANCED', 'JEE Advanced'),
    ]
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='GENERAL')
    item = models.OneToOneField(MarketplaceItem, on_delete=models.CASCADE, primary_key=True, related_name='mock_test_details')
    
    # Difficulty & Time
    level = models.CharField(max_length=50, choices=[('BEGINNER', 'Beginner'), ('INTERMEDIATE', 'Intermediate'), ('ADVANCED', 'Advanced')], default='BEGINNER')
    duration_minutes = models.PositiveIntegerField(help_text=_("Total time allowed in minutes"))
    
    # Scoring Config
    pass_percentage = models.PositiveIntegerField(default=50, help_text=_("Minimum % to pass"))
    has_negative_marking = models.BooleanField(default=False)
    negative_marking_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text=_("e.g. 0.25 for 25% deduction"))
    instructions = models.TextField(
        _("Instructions"), 
        blank=True, 
        help_text=_("Specific rules for this exam (e.g., Marking scheme, allowed items)."),
        default="""<ol>
        <li>Total duration of this examination is defined in the timer.</li>
        <li>The clock will be set at the server. The countdown timer in the top right corner of screen will display the remaining time available for you to complete the examination.</li>
        <li>The question palette displayed on the right side of screen will show the status of each question.</li>
        <li>You can mark a question for review to revisit it later.</li>
        <li><strong>Marking Scheme:</strong> Correct Answer: +1, Incorrect Answer: 0.</li>
        </ol>"""
            )
    # Leaderboard Logic
    ranking_weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, help_text=_("Multiplier for the global ranking (e.g., 1.5 for final exams)"))

    # Schedule
    start_datetime = models.DateTimeField(null=True, blank=True, help_text=_("When this test opens"))
    end_datetime = models.DateTimeField(null=True, blank=True, help_text=_("When this test closes"))

    def __str__(self):
        return f"Details for: {self.item.title}"

class TestSection(models.Model):
    """
    Tests are often divided into sections (e.g., 'Verbal Ability', 'Logic').
    """
    test = models.ForeignKey(MockTestAttributes, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(_("Section Title"), max_length=255)
    sort_order = models.PositiveIntegerField(default=0)
    section_duration = models.IntegerField(null=True, help_text="Time limit for this section in minutes")
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.title} ({self.test.item.title})"

class TestSyllabus(models.Model):
    """
    Tests are often divided into sections (e.g., 'Verbal Ability', 'Logic').
    """
    test = models.ForeignKey(MockTestAttributes, on_delete=models.CASCADE, related_name='syllabus')
    content = models.TextField("Syllabus")
    def __str__(self):
        return f"{self.content} ({self.test.item.title})"

class TestEligibility(models.Model):
    """
    Tests are often divided into sections (e.g., 'Verbal Ability', 'Logic').
    """
    test = models.ForeignKey(MockTestAttributes, on_delete=models.CASCADE, related_name='eligibility')
    content = models.TextField("Eligibility")
    def __str__(self):
        return f"{self.content} ({self.test.item.title})"

    

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
    DIFFICULTY_CHOICES = [('EASY', 'Easy'), ('MEDIUM', 'Medium'), ('HARD', 'Hard')]
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='MEDIUM')
    # NEW: Link to a passage (Optional, because not all questions have passages)
    passage = models.ForeignKey(ComprehensionPassage, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions')

    question_text = models.TextField(_("Question Text"))
    explanation = models.TextField(_("Explanation"), blank=True)
    
  
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MCQ)
    correct_answer_value = models.CharField(
        _("Correct Answer (Input)"), 
        max_length=255, 
        blank=True, 
        null=True,
        help_text=_("For Numeric/Input questions. Enter the exact correct value.")
    )
    marks = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"Q: {self.question_text[:50]}..."
    
class QuestionMedia(models.Model):
    """
    Supports multiple images per question.
    """
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='questions/images/')
    caption = models.CharField(max_length=255, blank=True, help_text=_("Optional description"))
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

class QuestionAudio(models.Model):
    """
    Supports multiple audio clips per question.
    """
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='audios')
    audio_file = models.FileField(upload_to='questions/audio/')
    label = models.CharField(max_length=100, blank=True, help_text=_("e.g., 'Speaker 1', 'Conversation A'"))

    def __str__(self):
        return self.label or "Audio Clip"

class QuestionOption(models.Model):
    """
    Options for MCQ questions.
    """
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(_("Option Text"), max_length=500)
    is_correct = models.BooleanField(default=False)
    option_image = models.ImageField(upload_to='options/images/', null=True, blank=True)

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
    audio_answer = models.FileField(upload_to='answers/audio/', null=True, blank=True)
    # 2. Numeric Answer (JEE)
    numeric_answer = models.CharField(max_length=255, null=True, blank=True)
    
    # 3. NEW: Essay/Subjective Answer (IELTS/CBSE)
    text_answer = models.TextField(null=True, blank=True, help_text=_("For Essay or Subjective questions"))
    
    is_correct = models.BooleanField(default=False)
    
    # Score awarded for this specific answer (useful for partial marking in CBSE)
    score_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_marked_for_review = models.BooleanField(default=False)

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