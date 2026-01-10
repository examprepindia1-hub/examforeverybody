from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, F
from .utils import get_leaderboard_data, get_user_rank

from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from mocktests.models import UserTestAttempt
from .models import Category
from django.db.models import Q
from django.core.paginator import Paginator

from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from marketplace.models import MarketplaceItem
from blog.models import Post  # <--- Import this
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_GET


def search(request):
    query = request.GET.get('q', '')
    
    # Initialize empty querysets
    all_items = MarketplaceItem.objects.none()
    blog_results = Post.objects.none()

    if query:
        # 1. Search Marketplace (Tests/Workshops)
        all_items = MarketplaceItem.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            is_active=True
        ).select_related('mock_test_details').order_by('-created')

        # 2. Search Blogs (Title or Content)
        blog_results = Post.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            status='published'
        ).order_by('-created_at')

    # Segregate Marketplace Items
    mock_tests = all_items.filter(item_type='MOCK_TEST')
    workshops = all_items.filter(item_type='WORKSHOP')
    
    # Pagination (Mainly for the 'All Items' tab if you wish, or just list them)
    # For simplicity, we are just passing the full lists to tabs for now.
    
    total_count = all_items.count() + blog_results.count()

    context = {
        'query': query,
        'total_count': total_count,
        'mock_tests': mock_tests,
        'workshops': workshops,
        'blogs': blog_results, # <--- Pass blogs to template
    }
    return render(request, 'core/search_results.html', context)

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
    # 1. Start with all active items AND annotate Average Rating immediately
    # This ensures 'avg_rating' is available for Featured, Popular, AND Workshops
    items = MarketplaceItem.objects.filter(is_active=True).annotate(
        avg_rating=Avg('testimonials__rating'),
        total_reviews=Count('testimonials', distinct=True),
        total_students=Count('enrollments', distinct=True) + F('base_enrollment_count')
    )

    # 2. Apply Category Filter (if clicked)
    category_slug = request.GET.get('category')
    if category_slug:
        items = items.filter(categories__slug=category_slug) # Changed 'value' to 'slug' (standard convention)

    # 3. Segregate for the UI Sections
    
    # Featured: Recently created
    featured_tests = items.filter(item_type='MOCK_TEST').order_by('-created')[:4]
    
    # Popular: Ordered by Enrollments
    # CRITICAL: Added distinct=True because we are now joining with testimonials too
    popular_exams = items.filter(item_type='MOCK_TEST').annotate(
        student_count=Count('enrollments', distinct=True) 
    ).order_by('-student_count')[:4]
    
    upcoming_workshops = items.filter(item_type='WORKSHOP')[:4]

    # 4. Fetch Categories
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
    all_posts = Post.objects.filter(categories=category, status='published')
    context = {
        'category': category,
        'mock_tests': all_items.filter(item_type='MOCK_TEST'),
        'workshops': all_items.filter(item_type='WORKSHOP'),
        'courses': all_items.filter(item_type='VIDEO_COURSE'),
        'notes': all_items.filter(item_type='NOTE'),
        'blog_posts': all_posts,
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


@login_required
def dashboard_recent_attempt_view(request):
    user = request.user
    
   

    recent_attempts = UserTestAttempt.objects.filter(
        user=user
    ).select_related('test__item').order_by('-modified')

    
    context = {
       
        'recent_attempts': recent_attempts,
        
    }
    return render(request, 'core/dashboard_recent_attempt.html', context)

def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')

def terms_of_service(request):
    return render(request, 'core/terms_of_service.html')

def cookie_policy(request):
    return render(request, 'core/cookie_policy.html')


def contact_support(request):
    if request.method == 'POST':
        # Placeholder for email sending logic
        messages.success(request, "Your message has been sent! Our support team will respond within 24 hours.")
        return render(request, 'core/contact_support.html')
    return render(request, 'core/contact_support.html')

def about_us(request):
    return render(request, 'core/about_us.html')

def careers(request):
    return render(request, 'core/careers.html')

def faq(request):
    return render(request, 'core/faq.html')


@require_GET
def robots_txt(request):
    """
    Generates a robots.txt file that points to the sitemap.
    """
    # 1. Define the rules
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /dashboard/",
        "Disallow: /billing/",
        "Allow: /",
        "",
        # 2. Dynamic Sitemap Link
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    
    return HttpResponse("\n".join(lines), content_type="text/plain")

@login_required
def leaderboard(request, slug=None):
    """
    Global Leaderboard:
    - Rank users by sum of scores from their MOST RECENT attempt on unique tests.
    - Only considers SUBMITTED attempts.
    - SUPPORTS FILTERS: Path param <slug> OR ?slug=<slug> (legacy support)
    """
    selected_slug = slug or request.GET.get('slug')
    
    # 0. Fetch available tests for the Filter Dropdown
    # Only show tests that actually have submitted attempts to avoid empty pages
    available_tests = MarketplaceItem.objects.filter(
        item_type='MOCK_TEST',
        mock_test_details__attempts__status='SUBMITTED'
    ).distinct().order_by('title')

    # 1. Fetch Data (Already enriched with rank, percentile, streak from utils)
    leaderboard_data = get_leaderboard_data(test_slug=selected_slug)

    # 2. Partition Data: Top 20 + User
    # The requirement is to show Top 20. If current user is not in Top 20, they should be the 21st item.
    
    top_20 = leaderboard_data[:20]
    final_leaderboard = list(top_20) # Copy to allow appending
    
    current_user_stats = None
    if request.user.is_authenticated:
        # Find user in the full list
        user_entry = next((item for item in leaderboard_data if item['user_id'] == request.user.id), None)
        
        if user_entry:
            current_user_stats = user_entry
            # Check if user is in top 20
            is_in_top_20 = any(item['user_id'] == request.user.id for item in top_20)
            if not is_in_top_20:
                final_leaderboard.append(user_entry)

    # For the template, we still partition for the "Top 3 Cards" vs "Table" view.
    # The table should show records from index 3 up to 20 (or 21).
    top_three = final_leaderboard[:3]
    rankings = final_leaderboard[3:] 

    context = {
        'top_three': top_three,
        'rankings': rankings,
        'user_stats': current_user_stats, # For the Personal Gradient Card
        'available_tests': available_tests,
        'selected_slug': selected_slug, 
    }
    return render(request, 'core/leaderboard.html', context)

def logout_success(request):
    """
    Page shown after a successful logout.
    """
    return render(request, 'account/logout_success.html')