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
def take_test(request, attempt_id):
    """
    The main exam interface. Loads all sections and questions.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status == UserTestAttempt.Status.SUBMITTED:
        return redirect('test_result', attempt_id=attempt.id)

    # Optimize queries: Fetch sections -> questions -> options
    test = attempt.test
    sections = TestSection.objects.filter(test=test).prefetch_related(
        Prefetch('questions', queryset=TestQuestion.objects.order_by('sort_order').prefetch_related('options'))
    ).order_by('sort_order')

    # Load existing answers to pre-fill the UI (Resume functionality)
    existing_answers = UserAnswer.objects.filter(attempt=attempt).values('question_id', 'selected_option_id', 'text_answer')
    answers_dict = {a['question_id']: a for a in existing_answers}

    context = {
        'attempt': attempt,
        'test': test,
        'sections': sections,
        'answers_json': json.dumps(answers_dict), # Pass to JS for restoring state
    }
    return render(request, 'mocktests/take_test.html', context)

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
        attempt.save()
        
        # Calculate Score (Basic Logic)
        # You can move this to a separate service or Celery task later
        calculate_score(attempt)
        
        return redirect('home') # TODO: Redirect to Result Page later

    return redirect('take_test', attempt_id=attempt_id)

def calculate_score(attempt):
    """
    Simple scoring logic helper.
    """
    total_score = 0
    for answer in attempt.answers.all():
        question = answer.question
        if question.question_type == 'MCQ' and answer.selected_option:
            if answer.selected_option.is_correct:
                total_score += question.marks
                answer.is_correct = True
                answer.score_awarded = question.marks
            else:
                # Handle negative marking here if needed
                pass
            answer.save()
            
    attempt.score = total_score
    attempt.is_passed = total_score >= attempt.test.pass_percentage
    attempt.save()