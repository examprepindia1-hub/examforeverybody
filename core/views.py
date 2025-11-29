from django.shortcuts import render
from marketplace.models import MarketplaceItem

def home(request):
    # Fetch active items for the homepage
    # Optimize query with select_related for linked data
    featured_tests = MarketplaceItem.objects.filter(
        item_type='MOCK_TEST', 
        is_active=True
    ).select_related('mock_test_details')[:4]
    
    upcoming_workshops = MarketplaceItem.objects.filter(
        item_type='WORKSHOP', 
        is_active=True
    )[:4]

    return render(request, 'core/home.html', {
        'featured_tests': featured_tests,
        'upcoming_workshops': upcoming_workshops
    })