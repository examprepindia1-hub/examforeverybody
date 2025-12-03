from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Prefetch
import json

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from .models import QuestionReport,MockTestAttributes, UserTestAttempt, TestSection, TestQuestion, UserAnswer, QuestionOption

@login_required
def start_test(request, slug):
    """
    Initializes the test. If an unfinished attempt exists, resume it.
    Otherwise, start a new one.
    """
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Security: Check Enrollment
    if not UserEnrollment.objects.filter(user=request.user, item=item).exists():
        return redirect('item_detail', slug=slug)

    test_details = get_object_or_404(MockTestAttributes, item=item)

    # 2. Check for existing incomplete attempt
    existing_attempt = UserTestAttempt.objects.filter(
        user=request.user, 
        test=test_details, 
        status=UserTestAttempt.Status.IN_PROGRESS
    ).first()

    if existing_attempt:
        return redirect('take_test', attempt_id=existing_attempt.id)

    # 3. Create new attempt
    attempt = UserTestAttempt.objects.create(
        user=request.user,
        test=test_details,
        status=UserTestAttempt.Status.IN_PROGRESS
    )
    return redirect('take_test', attempt_id=attempt.id)


@login_required
@require_POST
def save_answer(request):
    data = json.loads(request.body)
    attempt_id = data.get('attempt_id')
    question_id = data.get('question_id')
    option_id = data.get('option_id')
    text_input = data.get('text_input')
    
    # New field from frontend
    is_reviewed = data.get('is_reviewed', False) 

    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    question = get_object_or_404(TestQuestion, id=question_id)

    answer, created = UserAnswer.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults={
            'selected_option_id': option_id if option_id else None,
            'text_answer': text_input if text_input else '',
            'is_marked_for_review': is_reviewed  # Save the status
        }
    )
    
    return JsonResponse({'status': 'saved', 'answer_id': answer.id})


@login_required
@require_POST
def report_question(request):
    """
    AJAX View to handle question reporting
    """
    data = json.loads(request.body)
    question_id = data.get('question_id')
    reason = data.get('reason')

    if not reason:
        return JsonResponse({'status': 'error', 'message': 'Reason is required'}, status=400)

    question = get_object_or_404(TestQuestion, id=question_id)
    
    QuestionReport.objects.create(
        user=request.user,
        question=question,
        report_text=reason
    )
    
    return JsonResponse({'status': 'success', 'message': 'Report submitted. Thank you!'})

@login_required
def submit_test(request, attempt_id):
    """
    Final submission logic.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    if request.method == 'POST':
        attempt.status = UserTestAttempt.Status.SUBMITTED
        attempt.completed_at = timezone.now()
        
        
        # Calculate Score (Basic Logic)
        # You can move this to a separate service or Celery task later
        calculate_score(attempt)
        attempt.save()

        return redirect('test_result', attempt_id=attempt.id)

    return redirect('take_test', attempt_id=attempt_id)

@login_required
def start_test(request, slug):
    item = get_object_or_404(MarketplaceItem, slug=slug)
    if not UserEnrollment.objects.filter(user=request.user, item=item).exists():
        return redirect('item_detail', slug=slug)

    test_details = get_object_or_404(MockTestAttributes, item=item)

    # Get or Create Attempt
    attempt, created = UserTestAttempt.objects.get_or_create(
        user=request.user,
        test=test_details,
        status=UserTestAttempt.Status.IN_PROGRESS
    )

    # Logic: It is "Resume" only if they have answered at least 1 question
    has_started = attempt.answers.exists()

    context = {
        'attempt': attempt,
        'test': test_details,
        'item': item,
        'has_started': has_started, # Pass this to template
    }
    return render(request, 'mocktests/test_intro.html', context)

@login_required
def take_test(request, attempt_id):
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status == UserTestAttempt.Status.SUBMITTED:
        return redirect('test_result', attempt_id=attempt.id)

    test = attempt.test
    
    # --- FIX: Calculate Server-Side Remaining Time ---
    now = timezone.now()
    # Assuming started_at is set when created. 
    # If you want the timer to start ONLY when they enter this view, 
    # you would update started_at here if it's None/Old. 
    # For strict exams, we use Creation Time.
    
    elapsed = (now - attempt.started_at).total_seconds()
    total_duration_seconds = test.duration_minutes * 60
    remaining_seconds = max(0, int(total_duration_seconds - elapsed))

    # Auto-submit if time is up
    if remaining_seconds <= 0:
        return submit_test(request, attempt.id) # Reuse submit logic
    # -------------------------------------------------

    sections = TestSection.objects.filter(test=test).prefetch_related(
        Prefetch('questions', queryset=TestQuestion.objects.order_by('sort_order').prefetch_related('options', 'images', 'audios'))
    ).order_by('sort_order')

    existing_answers = UserAnswer.objects.filter(attempt=attempt).values(
        'question_id', 'selected_option_id', 'text_answer', 'is_marked_for_review'
    )
    answers_dict = {str(a['question_id']): a for a in existing_answers}

    context = {
        'attempt': attempt,
        'test': test,
        'sections': sections,
        'answers_json': json.dumps(answers_dict),
        'remaining_seconds': remaining_seconds, # Pass calculated time
    }
    return render(request, 'mocktests/take_test.html', context)


def calculate_score(attempt):
    """
    Grades the attempt by comparing UserAnswer with QuestionOption is_correct.
    """
    total_score = 0
    
    # Loop through all answers provided by the user
    for user_answer in attempt.answers.all():
        question = user_answer.question
        
        # Logic for Multiple Choice Questions
        if question.question_type == 'MCQ' and user_answer.selected_option:
            if user_answer.selected_option.is_correct:
                # Correct! Add marks
                total_score += question.marks
                user_answer.is_correct = True
                user_answer.score_awarded = question.marks
            else:
                # Wrong
                user_answer.is_correct = False
                user_answer.score_awarded = 0
            
            user_answer.save()
            
    # Update the attempt record
    attempt.score = total_score
    # Pass if score > 40% (or whatever logic you prefer)
    total_marks = sum(q.marks for q in TestQuestion.objects.filter(section__test=attempt.test))
    if total_marks > 0:
        percentage = (total_score / total_marks) * 100
        attempt.is_passed = percentage >= attempt.test.pass_percentage
    
    attempt.save()

@login_required
def test_result(request, attempt_id):
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status != UserTestAttempt.Status.SUBMITTED:
        return redirect('take_test', attempt_id=attempt.id)

    # 1. Calculate Stats
    total_questions = TestQuestion.objects.filter(section__test=attempt.test).count()
    correct_answers = attempt.answers.filter(is_correct=True).count()
    incorrect_answers = attempt.answers.filter(is_correct=False).exclude(selected_option=None, text_answer__exact='').count()
    skipped_answers = total_questions - (correct_answers + incorrect_answers)
    
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Time formatting
    time_taken = "N/A"
    if attempt.completed_at and attempt.created:
        duration = attempt.completed_at - attempt.created
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_taken = f"{hours:02}:{minutes:02}:{seconds:02}"

    # --- FIX: Build a complete list of ALL questions (Answered + Skipped) ---
    
    # A. Get all questions for this test
    all_questions = TestQuestion.objects.filter(
        section__test=attempt.test
    ).select_related('section').prefetch_related('options', 'images').order_by('section__sort_order', 'sort_order')

    # B. Get existing user answers and map them by Question ID for fast lookup
    user_answers_map = {
        a.question_id: a 
        for a in attempt.answers.select_related('selected_option').all()
    }

    # C. Construct the final analysis list
    analysis_list = []
    for question in all_questions:
        user_answer = user_answers_map.get(question.id)
        
        # Determine status
        selected_option = None
        if user_answer:
            selected_option = user_answer.selected_option
            if user_answer.is_correct:
                status = 'CORRECT'
            elif selected_option or user_answer.text_answer:
                status = 'WRONG'
            else:
                status = 'SKIPPED'
        else:
            status = 'SKIPPED'

        analysis_list.append({
            'question': question,
            'user_answer': user_answer,
            'selected_option': selected_option,
            'status': status
        })
    # -----------------------------------------------------------------------

    context = {
        'attempt': attempt,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'skipped_answers': skipped_answers,
        'accuracy': round(accuracy, 1),
        'time_taken': time_taken,
        'analysis_list': analysis_list,  # Pass the new combined list
    }
    
    return render(request, 'mocktests/test_result.html', context)