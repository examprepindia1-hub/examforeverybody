from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from mocktests.models import UserTestAttempt

def home(request):
    """
    Root URL ('/').
    Smart switch: Logged-in -> Dashboard, Guest -> Landing Page.
    """
    if request.user.is_authenticated:
        return dashboard_view(request)
    else:
        return explore(request) # Re-use the explore view logic

def explore(request):
    """
    The public catalog/landing page. 
    Accessible at '/explore/' for logged-in users.
    """
    featured_tests = MarketplaceItem.objects.filter(
        item_type='MOCK_TEST', is_active=True
    ).select_related('mock_test_details')[:4]
    
    upcoming_workshops = MarketplaceItem.objects.filter(
        item_type='WORKSHOP', is_active=True
    )[:4]

    return render(request, 'core/home.html', {
        'featured_tests': featured_tests,
        'upcoming_workshops': upcoming_workshops
    })

@login_required
def dashboard_view(request):
    # ... (Keep your existing dashboard logic from the previous step) ...
    user = request.user
    my_enrollments = UserEnrollment.objects.filter(user=user, is_active=True).select_related('item').order_by('-created')[:6]
    recent_attempts = UserTestAttempt.objects.filter(user=user).select_related('test__item').order_by('-modified')[:5]
    
    stats = {
        'enrolled_count': my_enrollments.count(),
        'tests_taken': UserTestAttempt.objects.filter(user=user, status='SUBMITTED').count(),
        'avg_score': UserTestAttempt.objects.filter(user=user, status='SUBMITTED').aggregate(Avg('score'))['score__avg'] or 0
    }

    context = {
        'enrollments': my_enrollments,
        'recent_attempts': recent_attempts,
        'stats': stats,
    }
    return render(request, 'core/dashboard.html', context)