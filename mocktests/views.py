from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Prefetch
import json

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from .models import (
    QuestionReport, MockTestAttributes, UserTestAttempt, 
    TestSection, TestQuestion, UserAnswer, QuestionOption
)
from .services import get_exam_strategy  # <--- The Strategy Factory

@login_required
def start_test(request, slug):
    """
    Initializes the test. Handles enrollment checks and resuming.
    """
    item = get_object_or_404(MarketplaceItem, slug=slug)
    
    # 1. Enrollment Check
    if not UserEnrollment.objects.filter(user=request.user, item=item).exists():
        return redirect('item_detail', slug=slug)

    test_details = get_object_or_404(MockTestAttributes, item=item)

    # 2. Get or Create Attempt
    attempt, created = UserTestAttempt.objects.get_or_create(
        user=request.user,
        test=test_details,
        status=UserTestAttempt.Status.IN_PROGRESS
    )

    # 3. Strategy Hook (Optional)
    # If SAT, we might need to assign the initial "Routing Module" here.
    # strategy = get_exam_strategy(test_details.exam_type)
    # strategy.initialize_attempt(attempt) 

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
    
    if attempt.status == UserTestAttempt.Status.SUBMITTED:
        return redirect('test_result', attempt_id=attempt.id)

    test = attempt.test
    
    # 1. Get the correct Strategy (SAT, IELTS, or GENERAL)
    strategy = get_exam_strategy(test.exam_type)

    # 2. Timer Logic (Server-Side Calculation)
    now = timezone.now()
    if not attempt.started_at:
        attempt.started_at = now
        attempt.save()

    elapsed = (now - attempt.started_at).total_seconds()
    total_duration_seconds = test.duration_minutes * 60
    remaining_seconds = max(0, int(total_duration_seconds - elapsed))

    if remaining_seconds <= 0:
        return submit_test(request, attempt.id)

    # 3. Fetch Data (Optimized)
    # For Adaptive tests, we might filter sections differently here later.
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
        'remaining_seconds': remaining_seconds,
    }
    
    # 4. Render the specific template for this exam type
    template_name = strategy.get_take_test_template()
    return render(request, template_name, context)


@login_required
@require_POST
def save_answer(request):
    """
    AJAX Endpoint: Saves answers (Text, Radio, Audio)
    """
    # A. Handle File Upload (Audio/Speaking)
    if request.content_type.startswith('multipart/form-data'):
        attempt_id = request.POST.get('attempt_id')
        question_id = request.POST.get('question_id')
        audio_file = request.FILES.get('audio_data')
        
        attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
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

        attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
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

    if request.method == 'POST' or attempt.status != UserTestAttempt.Status.SUBMITTED:
        # 1. Get Strategy
        strategy = get_exam_strategy(test.exam_type)
        
        # 2. Calculate Score (Delegated to Strategy)
        # This handles SAT scaling, IELTS bands, or simple percentage
        result_data = strategy.calculate_score(attempt)
        
        # 3. Update Attempt
        attempt.status = UserTestAttempt.Status.SUBMITTED
        attempt.completed_at = timezone.now()
        attempt.score = result_data['score']
        
        # Determine Pass/Fail (Strategy can also handle this if logic is complex)
        # Simple default logic:
        attempt.is_passed = attempt.score >= test.pass_percentage
        
        attempt.save()

        return redirect('test_result', attempt_id=attempt.id)

    return redirect('take_test', attempt_id=attempt_id)


@login_required
def test_result(request, attempt_id):
    """
    Displays the result using the strategy-specific template.
    """
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status != UserTestAttempt.Status.SUBMITTED:
        return redirect('take_test', attempt_id=attempt.id)

    # 1. Get Strategy
    strategy = get_exam_strategy(attempt.test.exam_type)

    # 2. Common Stats (Useful for all templates)
    total_questions = TestQuestion.objects.filter(section__test=attempt.test).count()
    correct_answers = attempt.answers.filter(is_correct=True).count()
    incorrect_answers = attempt.answers.filter(is_correct=False).exclude(selected_option=None, text_answer__exact='').count()
    skipped_answers = total_questions - (correct_answers + incorrect_answers)
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    time_taken = "N/A"
    if attempt.completed_at and attempt.started_at:
        duration = attempt.completed_at - attempt.started_at
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_taken = f"{hours:02}:{minutes:02}:{seconds:02}"

    # 3. Detailed Analysis (List building)
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
    }
    
    # 4. Render Strategy Specific Template
    # (e.g. mocktests/exams/sat/result.html)
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