from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import Sum, Max
from .models import UserTestAttempt, UserRankMetric

def recalculate_user_rank(user):
    """
    Recalculates the UserRankMetric for a specific user.
    Logic: Sum of scores from the LATEST submitted attempt of each unique test.
    """
    # 1. Fetch all submitted attempts for this user
    attempts = UserTestAttempt.objects.filter(
        user=user, 
        status='SUBMITTED'
    ).order_by('test__item__id', '-created') # Group by test, then latest

    # 2. Filter in Python to get only the latest unique attempt per test
    # (Django ORM doesn't support 'DISTINCT ON' cross-db easily, so Python is safer for consistency)
    unique_attempts = {}
    for attempt in attempts:
        test_id = attempt.test_id
        if test_id not in unique_attempts:
            unique_attempts[test_id] = attempt
    
    # 3. Calculate Stats
    total_score = sum(a.score for a in unique_attempts.values() if a.score)
    tests_taken = len(unique_attempts)
    avg_score = total_score / tests_taken if tests_taken > 0 else 0

    # 4. Update Metric Table (Atomic)
    with transaction.atomic():
        metric, created = UserRankMetric.objects.get_or_create(user=user)
        metric.total_xp = int(total_score)
        metric.tests_taken_count = tests_taken
        metric.avg_score = avg_score
        metric.save()

@receiver(post_save, sender=UserTestAttempt)
def update_rank_on_submission(sender, instance, **kwargs):
    """
    Triggered whenever an attempt is saved.
    Only recalculate if status is SUBMITTED.
    """
    if instance.status == 'SUBMITTED':
        recalculate_user_rank(instance.user)
