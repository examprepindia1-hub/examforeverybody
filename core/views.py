from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from mocktests.models import UserTestAttempt
from .models import Category

def home(request):
    """
    Smart switch: Logged-in -> Dashboard, Guest -> Explore Page.
    """
    if request.user.is_authenticated:
        return dashboard_view(request)
    else:
        return explore(request)

def explore(request):
    """
    The public catalog/landing page with filtering.
    """
    # 1. Start with all active items
    items = MarketplaceItem.objects.filter(is_active=True)

    # 2. Apply Category Filter (if clicked)
    category_slug = request.GET.get('category')
    if category_slug:
        items = items.filter(categories__value=category_slug)

    # 3. Segregate for the UI Sections
    featured_tests = items.filter(item_type='MOCK_TEST').order_by('-created')[:4]
    
    popular_exams = items.filter(item_type='MOCK_TEST').annotate(
        student_count=Count('enrollments')
    ).order_by('-student_count')[:4]
    
    upcoming_workshops = items.filter(item_type='WORKSHOP')[:4]

    # 4. Fetch Categories (FIXED THE CRASH HERE)
    # We use 'items' because related_name='items' is defined in MarketplaceItem model
    categories = Category.objects.annotate(
        total_items=Count('items', filter=Q(items__is_active=True))
    ).order_by('-total_items')[:12]

    context = {
        'featured_tests': featured_tests,
        'popular_exams': popular_exams,
        'upcoming_workshops': upcoming_workshops,
        'categories': categories,
        'selected_category': category_slug,
    }
    return render(request, 'core/home.html', context)

def category_detail(request, slug):
    """
    Dedicated page for a single category (Linked from the 'Explore' button).
    """
    category = get_object_or_404(Category, slug=slug)
    all_items = MarketplaceItem.objects.filter(categories=category, is_active=True)
    
    context = {
        'category': category,
        'mock_tests': all_items.filter(item_type='MOCK_TEST'),
        'workshops': all_items.filter(item_type='WORKSHOP'),
        'courses': all_items.filter(item_type='VIDEO_COURSE'),
        'notes': all_items.filter(item_type='NOTE'),
    }
    return render(request, 'core/category_detail.html', context)

@login_required
def dashboard_view(request):
    user = request.user
    
    my_enrollments = UserEnrollment.objects.filter(
        user=user, is_active=True
    ).select_related('item').order_by('-created')[:6]

    recent_attempts = UserTestAttempt.objects.filter(
        user=user
    ).select_related('test__item').order_by('-modified')[:5]

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