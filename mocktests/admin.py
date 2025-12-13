import pandas as pd
from django import forms
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

from .models import (
    MockTestAttributes, TestSection, TestQuestion, 
    QuestionOption, UserTestAttempt, QuestionReport, 
    QuestionAudio, QuestionMedia, UserAnswer
)

# --- FORMS ---

class ImportQuestionsForm(forms.Form):
    file = forms.FileField(
        label="Upload File (Excel or CSV)",
        help_text="Supported formats: .xlsx, .xls, .csv"
    )

# --- 1. Content Management Inlines ---

class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4  # Show 4 empty slots for options by default

class QuestionImageInline(admin.TabularInline):
    model = QuestionMedia
    extra = 1  # Show 1 empty slot by default

class QuestionAudioInline(admin.TabularInline):
    model = QuestionAudio
    extra = 1

class TestQuestionInline(admin.TabularInline):
    model = TestQuestion
    fields = ('question_text', 'question_type', 'marks', 'sort_order')
    extra = 0
    show_change_link = True # Allow clicking to edit full question details

class TestSectionInline(admin.StackedInline):
    model = TestSection
    extra = 1

# --- 2. Model Admins ---

@admin.register(TestQuestion)
class TestQuestionAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'section', 'question_type', 'marks')
    list_filter = ('section', 'question_type')
    search_fields = ('question_text',)
    # Add the new inlines here
    inlines = [QuestionImageInline, QuestionAudioInline, QuestionOptionInline]
    
    def short_text(self, obj):
        return obj.question_text[:50] + "..." if obj.question_text else ""

@admin.register(TestSection)
class TestSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'test', 'sort_order')
    list_filter = ('test',)
    search_fields = ('title',)
    inlines = [TestQuestionInline]
    
    # Enable the "Import" button on the list view
    change_list_template = "admin/section_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('import-questions/', self.import_questions, name="mocktests_section_import"),
            path('download-template/', self.download_template, name="mocktests_section_download_template"),
        ]
        return my_urls + urls

    def download_template(self, request):
        # Create a sample DataFrame for the template
        data = {
            'Section_ID': [1, 1],
            'Question_Text': ['What is 2+2?', 'Sample Question 2'],
            'Type': ['MCQ', 'MCQ'],
            'Option_A': ['3', 'Option A Text'],
            'Option_B': ['4', 'Option B Text'],
            'Option_C': ['5', 'Option C Text'],
            'Option_D': ['6', 'Option D Text'],
            'Correct_Option': ['B', 'A'],
            'Marks': [1, 1],
            'Explanation': ['Basic math.', 'Explanation here.']
        }
        df = pd.DataFrame(data)
        
        # Create response as Excel file
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=sat_question_template.xlsx'
        
        # Write to response
        df.to_excel(response, index=False)
        return response

    def import_questions(self, request):
        if request.method == "POST":
            file = request.FILES.get("file")
            
            if not file:
                self.message_user(request, "Please upload a file.", level=messages.ERROR)
                return redirect("..")

            try:
                # 1. DETECT FILE TYPE
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(file)
                else:
                    self.message_user(request, "Unsupported file format. Please upload .csv or .xlsx", level=messages.ERROR)
                    return redirect("..")
                
                # 2. CLEANING: Remove NaN values
                df = df.where(pd.notnull(df), None)

                count = 0
                
                # 3. ITERATE
                for index, row in df.iterrows():
                    # Get Section
                    try:
                        section_id = int(row['Section_ID']) if row['Section_ID'] else None
                        section = TestSection.objects.get(id=section_id)
                    except (TestSection.DoesNotExist, ValueError):
                        continue # Skip invalid rows

                    # Create Question
                    q = TestQuestion.objects.create(
                        section=section,
                        question_text=row['Question_Text'],
                        question_type=str(row['Type']).strip().upper(),
                        marks=row['Marks'] if row['Marks'] else 1,
                        explanation=row.get('Explanation', ''),
                        sort_order=index + 1
                    )

                    # Create Options (Only for MCQ)
                    if q.question_type == 'MCQ':
                        correct_opt = str(row['Correct_Option']).strip().upper() if row['Correct_Option'] else ''
                        
                        options_map = {
                            'A': row.get('Option_A'),
                            'B': row.get('Option_B'),
                            'C': row.get('Option_C'),
                            'D': row.get('Option_D')
                        }

                        for key, text in options_map.items():
                            if text:
                                QuestionOption.objects.create(
                                    question=q,
                                    option_text=text,
                                    is_correct=(key == correct_opt)
                                )
                    count += 1
                
                self.message_user(request, f"Successfully imported {count} questions from {file.name}!")
                return redirect("..")
                
            except Exception as e:
                self.message_user(request, f"Error processing file: {e}", level=messages.ERROR)
                return redirect("..")

        form = ImportQuestionsForm()
        payload = {"form": form}
        return render(request, "admin/excel_import_form.html", payload)

@admin.register(MockTestAttributes)
class MockTestAdmin(admin.ModelAdmin):
    # Added 'exam_type' so you can see which test is SAT/IELTS in the list
    list_display = ('item', 'exam_type', 'level', 'duration_minutes', 'pass_percentage')
    inlines = [TestSectionInline]

# --- 3. Student Progress & Reports ---

class UserAnswerInline(admin.TabularInline):
    model = UserAnswer
    readonly_fields = ('question', 'selected_option', 'text_answer', 'is_correct', 'is_marked_for_review')
    can_delete = False
    extra = 0
    max_num = 50 

@admin.register(UserTestAttempt)
class UserTestAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'score', 'is_passed', 'status', 'completed_at')
    list_filter = ('status', 'is_passed', 'test')
    search_fields = ('user__email', 'test__item__title')
    readonly_fields = ('score', 'is_passed', 'started_at', 'completed_at')
    
    inlines = [UserAnswerInline]

@admin.register(QuestionReport)
class QuestionReportAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'is_resolved', 'created')
    list_filter = ('is_resolved',)
    list_editable = ('is_resolved',)
    readonly_fields = ('report_text',)