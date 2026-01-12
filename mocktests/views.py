from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Prefetch
import json
from django.db import transaction

from marketplace.models import MarketplaceItem, Testimonial
from enrollments.models import UserEnrollment
from .models import (
    QuestionReport, MockTestAttributes, UserTestAttempt, 
    TestSection, TestQuestion, UserAnswer
)
from .services import get_exam_strategy

@login_required
def start_test(request, slug):
    """
    Initializes the test. Handles enrollment checks and resuming.
    """
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Enrollment Check
    if not UserEnrollment.objects.filter(user=request.user, item=item).exists():
        return redirect('marketplace:item_detail', slug=slug)

    test_details = get_object_or_404(MockTestAttributes, item=item)

    # 2. Get or Create Attempt
    attempt, created = UserTestAttempt.objects.get_or_create(
        user=request.user,
        test=test_details,
        status=UserTestAttempt.Status.IN_PROGRESS
    )

    # 3. Mark start time immediately if new
    if created or not attempt.started_at:
        attempt.started_at = timezone.now()
        attempt.save()

    has_started = attempt.answers.exists()

    context = {
        'attempt': attempt,
        'test': test_details,
        'item': item,
        'has_started': has_started, 
    }
    return render(request, 'mocktests/test_intro.html', context)


@login_required
def take_test(request, attempt_id):
    """
    The main Exam Engine. Loads the correct UI based on Exam Type.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    # Redirect if already submitted
    if attempt.status == UserTestAttempt.Status.SUBMITTED:
        return redirect('test_result', attempt_id=attempt.id)

    test = attempt.test
    
    # 1. Timer Logic (Server-Side Calculation)
    now = timezone.now()
    if not attempt.started_at:
        attempt.started_at = now
        attempt.save()

    elapsed = (now - attempt.started_at).total_seconds()
    total_duration_seconds = test.duration_minutes * 60
    remaining_seconds = max(0, int(total_duration_seconds - elapsed))

    # Auto-submit if time is up
    if remaining_seconds <= 0:
        return submit_test(request, attempt.id)

    # 2. Get Strategy (SAT, IELTS, or GENERAL)
    strategy = get_exam_strategy(test.exam_type)

    # 3. Fetch Data (Optimized with Prefetch)
    sections = TestSection.objects.filter(test=test).prefetch_related(
        Prefetch('questions', queryset=TestQuestion.objects.order_by('sort_order').prefetch_related('options', 'images', 'audios'))
    ).order_by('sort_order')

    # Load existing answers to repopulate the UI
    existing_answers = UserAnswer.objects.filter(attempt=attempt).values(
        'question_id', 'selected_option_id', 'text_answer', 'is_marked_for_review'
    )
    answers_dict = {str(a['question_id']): a for a in existing_answers}

    context = {
        'attempt': attempt,
        'test': test,
        'sections': sections,
        'answers_json': json.dumps(answers_dict),
        'remaining_seconds': remaining_seconds,
    }
    
    template_name = strategy.get_take_test_template()
    return render(request, template_name, context)


@login_required
@require_POST
def save_answer(request):
    """
    AJAX Endpoint: Saves answers (Text, Radio, Audio).
    Includes Security & Timer checks.
    """
    # 1. Common Security Check Helper
    def get_valid_attempt(att_id):
        att = get_object_or_404(UserTestAttempt, id=att_id, user=request.user)
        
        # Check A: Is it already submitted?
        if att.status == UserTestAttempt.Status.SUBMITTED:
            return None, JsonResponse({'status': 'error', 'message': 'Test already submitted'}, status=403)
        
        # Check B: Has the time expired? (+2 minute buffer for network latency)
        if att.test.duration_minutes > 0 and att.started_at:
            elapsed = (timezone.now() - att.started_at).total_seconds()
            allowed = (att.test.duration_minutes * 60) + 120 
            if elapsed > allowed:
                return None, JsonResponse({'status': 'error', 'message': 'Time limit exceeded'}, status=403)
                
        return att, None

    # A. Handle File Upload (Audio/Speaking)
    if request.content_type.startswith('multipart/form-data'):
        attempt_id = request.POST.get('attempt_id')
        question_id = request.POST.get('question_id')
        audio_file = request.FILES.get('audio_data')
        
        attempt, error_response = get_valid_attempt(attempt_id)
        if error_response: return error_response

        question = get_object_or_404(TestQuestion, id=question_id)
        
        answer, created = UserAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'audio_answer': audio_file}
        )
        return JsonResponse({'status': 'uploaded', 'url': answer.audio_answer.url})

    # B. Handle JSON (MCQ / Text)
    else:
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        question_id = data.get('question_id')
        option_id = data.get('option_id')
        text_input = data.get('text_input')
        is_reviewed = data.get('is_reviewed', False)

        attempt, error_response = get_valid_attempt(attempt_id)
        if error_response: return error_response

        question = get_object_or_404(TestQuestion, id=question_id)

        answer, created = UserAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'selected_option_id': option_id if option_id else None,
                'text_answer': text_input if text_input else '',
                'is_marked_for_review': is_reviewed
            }
        )
        
        return JsonResponse({'status': 'saved', 'answer_id': answer.id})


@login_required
def submit_test(request, attempt_id):
    """
    Calculates score based on strategy and marks attempt as SUBMITTED.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    test = attempt.test

    # Process if POST request OR if it's an auto-submit (via GET from take_test)
    # Use atomic transaction and select_for_update to prevent double submissions
    with transaction.atomic():
        # Re-fetch with lock
        attempt = UserTestAttempt.objects.select_for_update().get(id=attempt_id)
        
        if request.method == 'POST' or attempt.status != UserTestAttempt.Status.SUBMITTED:
            # Double check status inside lock
            if attempt.status == UserTestAttempt.Status.SUBMITTED:
                return redirect('exam_feedback', attempt_id=attempt.id)

            strategy = get_exam_strategy(test.exam_type)
            
            # 1. Grade & Calculate Score
            # This calls grade_answers() internally in our new services.py
            result_data = strategy.calculate_score(attempt)
            
            # 2. Finalize Attempt
            attempt.status = UserTestAttempt.Status.SUBMITTED
            attempt.completed_at = timezone.now()
            attempt.score = result_data['score']
            
            # 3. Pass/Fail Logic
            if isinstance(result_data.get('passed'), bool):
                 attempt.is_passed = result_data['passed']
            else:
                 # Fallback
                 attempt.is_passed = attempt.score >= test.pass_percentage
            
            attempt.save()
    
            return redirect('exam_feedback', attempt_id=attempt.id)

    return redirect('take_test', attempt_id=attempt_id)


@login_required
def exam_feedback(request, attempt_id):
    """
    Intermediary page to collect feedback before showing results.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    # Security: Cannot give feedback if not submitted
    if attempt.status != UserTestAttempt.Status.SUBMITTED:
        return redirect('take_test', attempt_id=attempt.id)

    # Check if user has already given feedback for this Item
    # If yes, we can choose to show it or let them update it.
    # For now, we will pass the existing one to the template if it exists.
    existing_review = Testimonial.objects.filter(
        user=request.user, 
        item=attempt.test.item
    ).first()

    if request.method == "POST":
        # 1. Get Data
        rating = request.POST.get('rating')
        text = request.POST.get('feedback', '')
        
        # 2. Save Testimonial (Update or Create)
        if rating:
            user_country = getattr(request.user, 'country', 'India') # Fallback if country field is empty
            
            Testimonial.objects.update_or_create(
                user=request.user,
                item=attempt.test.item,
                defaults={
                    'rating': int(rating),
                    'text': text,
                    'country': str(user_country) if user_country else 'India'
                }
            )
        
        # 3. Proceed to Result
        return redirect('test_result', attempt_id=attempt.id)

    context = {
        'attempt': attempt,
        'existing_review': existing_review
    }
    return render(request, 'mocktests/feedback_page.html', context)


@login_required
def test_result(request, attempt_id):
    """
    Displays the result using the strategy-specific template.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    # Prevent viewing result if test isn't finished
    if attempt.status != UserTestAttempt.Status.SUBMITTED:
        return redirect('take_test', attempt_id=attempt.id)

    strategy = get_exam_strategy(attempt.test.exam_type)

    # 1. Basic Stats
    total_questions = TestQuestion.objects.filter(section__test=attempt.test).count()
    correct_answers = attempt.answers.filter(is_correct=True).count()
    
    # Count incorrect (excluding skipped/empty)
    incorrect_answers = attempt.answers.filter(is_correct=False).exclude(
        selected_option__isnull=True, 
        text_answer__exact=''
    ).count()
    
    skipped_answers = total_questions - (correct_answers + incorrect_answers)
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    time_taken = "N/A"
    if attempt.completed_at and attempt.started_at:
        duration = attempt.completed_at - attempt.started_at
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_taken = f"{hours:02}:{minutes:02}:{seconds:02}"

    # 2. Detailed Question Analysis
    all_questions = TestQuestion.objects.filter(
        section__test=attempt.test
    ).select_related('section').prefetch_related('options', 'images').order_by('section__sort_order', 'sort_order')

    user_answers_map = {a.question_id: a for a in attempt.answers.select_related('selected_option').all()}
    
    analysis_list = []
    for question in all_questions:
        user_answer = user_answers_map.get(question.id)
        selected_option = None
        status = 'SKIPPED'
        
        if user_answer:
            selected_option = user_answer.selected_option
            if user_answer.is_correct:
                status = 'CORRECT'
            elif selected_option or (user_answer.text_answer and user_answer.text_answer.strip()):
                status = 'WRONG'
        
        analysis_list.append({
            'question': question,
            'user_answer': user_answer,
            'selected_option': selected_option,
            'status': status
        })

    context = {
        'attempt': attempt,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'skipped_answers': skipped_answers,
        'accuracy': round(accuracy, 1),
        'time_taken': time_taken,
        'analysis_list': analysis_list,
        'score_details': attempt.score, # Pass score for templates
    }
    
    # 3. Use Strategy Template
    template_name = strategy.get_result_template()
    return render(request, template_name, context)

@login_required
@require_POST
def report_question(request):
    data = json.loads(request.body)
    question_id = data.get('question_id')
    reason = data.get('reason')

    if not reason:
        return JsonResponse({'status': 'error', 'message': 'Reason is required'}, status=400)

    question = get_object_or_404(TestQuestion, id=question_id)
    QuestionReport.objects.create(user=request.user, question=question, report_text=reason)
    
    return JsonResponse({'status': 'success', 'message': 'Report submitted.'})