from django.contrib import admin
from .models import (
    MockTestAttributes, TestSection, TestQuestion, 
    QuestionOption, UserTestAttempt, QuestionReport
)

# --- 1. Content Management ---

class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4  # Show 4 empty slots for options by default

@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'section', 'question_type', 'marks', 'sort_order')
    list_filter = ('section__test', 'question_type')
    search_fields = ('question_text',)
    inlines = [QuestionOptionInline]
    
    def short_text(self, obj):
        return obj.question_text[:50] + "..."

class TestQuestionInline(admin.TabularInline):
    model = TestQuestion
    fields = ('question_text', 'question_type', 'marks', 'sort_order')
    extra = 0
    show_change_link = True # Allow clicking to edit full question details

class TestSectionInline(admin.StackedInline):
    model = TestSection
    extra = 1

@admin.register(MockTestAttributes)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ('item', 'level', 'duration_minutes', 'pass_percentage')
    inlines = [TestSectionInline]

# --- 2. Student Progress & Reports ---

class UserAnswerInline(admin.TabularInline):
    model = "mocktests.UserAnswer" # String reference to avoid circular import issues
    readonly_fields = ('question', 'selected_option', 'text_answer', 'is_correct', 'is_marked_for_review')
    can_delete = False
    extra = 0

@admin.register(UserTestAttempt)
class UserTestAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'score', 'is_passed', 'status', 'completed_at')
    list_filter = ('status', 'is_passed', 'test')
    readonly_fields = ('score', 'is_passed', 'started_at', 'completed_at')
    
    # This creates a nice view of their answers inside the attempt page
    # Note: Requires importing UserAnswer model properly or removing if complex
    # inlines = [UserAnswerInline] 

@admin.register(QuestionReport)
class QuestionReportAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'is_resolved', 'created')
    list_filter = ('is_resolved',)
    list_editable = ('is_resolved',)
    readonly_fields = ('report_text',)