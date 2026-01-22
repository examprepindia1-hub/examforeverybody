from django.views.generic import DetailView, ListView
from django.db.models import Avg, Max
from django.utils import timezone
from .models import MarketplaceItem, Testimonial
from enrollments.models import UserEnrollment
from billing.models import Order
from mocktests.models import UserTestAttempt, TestQuestion

from django.db.models import Count, Q
from core.models import Category
from django.contrib.auth import get_user_model

User = get_user_model()

class ItemListView(ListView):
    model = MarketplaceItem
    template_name = 'marketplace/item_list.html'
    context_object_name = 'items'
    paginate_by = 9  # 3x3 Grid

    def get_queryset(self):
        qs = MarketplaceItem.objects.filter(is_active=True)
        qs = qs.prefetch_related('categories', 'testimonials', 'mock_test_details')
        
        # 1. Category Filter (Multi-select)
        categories = self.request.GET.getlist('category')
        if categories:
            qs = qs.filter(categories__slug__in=categories)
        
        # 2. Search Filter
        query = self.request.GET.get('s') or self.request.GET.get('search')
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

        # 3. Item Type Filter (Optional, for "Course Type" sidebar)
        item_types = self.request.GET.getlist('type') # Checkbox allow multiple
        if item_types:
            qs = qs.filter(item_type__in=item_types)

        # 4. Instructor Filter
        instructors = self.request.GET.getlist('instructor')
        if instructors:
            qs = qs.filter(instructor__id__in=instructors)

        # 5. Additional Filters (Free, Certificate, etc.)
        additional_filters = self.request.GET.getlist('additional')
        if 'free' in additional_filters:
            qs = qs.filter(price=0)
        if 'certificate' in additional_filters:
            qs = qs.filter(has_certificate=True)

        # 6. Price Range Filter
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
            
        return qs.distinct().order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Sidebar: Categories with counts
        context['categories'] = Category.objects.annotate(
            count=Count('items', filter=Q(items__is_active=True))
        ).filter(count__gt=0).order_by('display_name')
        
        # Sidebar: Item Types with counts
        # We manually construct this because ItemType is a ChoiceField, not a model
        # But we can aggregate existing items to get counts
        type_counts = MarketplaceItem.objects.filter(is_active=True).values('item_type').annotate(count=Count('id'))
        # Map back to display names
        type_map = dict(MarketplaceItem.ItemType.choices)
        context['item_types'] = [
            {
                'code': t['item_type'],
                'label': type_map.get(t['item_type'], t['item_type']),
                'count': t['count']
            }
            for t in type_counts
        ]

        # Sidebar: Instructors with counts
        context['instructors'] = User.objects.filter(
            marketplace_items__is_active=True
        ).annotate(
            count=Count('marketplace_items', filter=Q(marketplace_items__is_active=True))
        ).distinct().order_by('first_name')



        context['selected_categories'] = self.request.GET.getlist('category')
        context['search_query'] = self.request.GET.get('s', '')
        context['selected_types'] = self.request.GET.getlist('type')
        context['selected_instructors'] = [int(i) for i in self.request.GET.getlist('instructor') if i.isdigit()]
        context['selected_additional'] = self.request.GET.getlist('additional')
        context['min_price'] = self.request.GET.get('min_price', '')
        context['max_price'] = self.request.GET.get('max_price', '')
        
        # Heading Logic - Fixed to maintain heading even with search
        heading = "Marketplace"
        selected_types = self.request.GET.getlist('type')
        if len(selected_types) == 1:
            # Find display name for the single selected type
            # MarketplaceItem.ItemType.choices is a list of (value, label) tuples
            type_map = dict(MarketplaceItem.ItemType.choices)
            type_label = type_map.get(selected_types[0])
            if type_label:
                heading = f"{type_label}s" # Pluralize simple way
        elif len(selected_types) > 1:
            # Multiple types selected, keep generic heading
            heading = "Marketplace"

        context['heading'] = heading
        return context

class ItemDetailView(DetailView):
    model = MarketplaceItem
    template_name = 'marketplace/item_detail.html'
    context_object_name = 'item'

    def get_queryset(self):
        return MarketplaceItem.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        user = self.request.user
        
        # 1. Reviews & Ratings
        reviews = Testimonial.objects.filter(item=item).order_by('-created')
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        context['reviews'] = reviews
        context['avg_rating'] = avg_rating if avg_rating else 0
        context['review_count'] = reviews.count()

        # 2. Enrollment Check
        is_enrolled = False
        latest_order_status = None

        if user.is_authenticated:
            is_enrolled = UserEnrollment.objects.filter(user=user, item=item).exists()
            
            # 3. IF NOT ENROLLED: Check for Pending/Failed orders
            if not is_enrolled:
                last_order = Order.objects.filter(
                    user=user, 
                    items__item=item
                ).order_by('-created').first()

                if last_order:
                    latest_order_status = last_order.status

        context['is_enrolled'] = is_enrolled
        context['latest_order_status'] = latest_order_status
        
        # 4. Mock Test Specific Data
        if (item.item_type == MarketplaceItem.ItemType.MOCK_TEST or item.item_type == MarketplaceItem.ItemType.SCHOLARSHIP_TEST) and hasattr(item, 'mock_test_details'):
            details = item.mock_test_details
            
            # Stats (Total Questions, Total Marks)
            # Efficiently sum up questions and marks from all sections
            questions = TestQuestion.objects.filter(section__test=details)
            context['total_questions'] = questions.count()
            
            total_marks = 0
            for q in questions:
                total_marks += q.marks
            context['total_marks'] = total_marks

            # Quick Stats (Attempts, Scores)
            attempts = UserTestAttempt.objects.filter(test=details, status=UserTestAttempt.Status.SUBMITTED)
            total_attempts = attempts.count()
            
            agg = attempts.aggregate(Avg('score'), Max('score'))
            avg_score = agg['score__avg'] or 0
            top_score = agg['score__max'] or 0
            
            pass_count = attempts.filter(is_passed=True).count()
            pass_rate = (pass_count / total_attempts * 100) if total_attempts > 0 else 0

            context['quick_stats'] = {
                'total_attempts': total_attempts,
                'avg_score': round(avg_score, 1),
                'top_score': round(top_score, 1),
                'pass_rate': round(pass_rate, 1)
            }

            # Time Checks (For Buttons)
            now = timezone.now()
            context['is_future_test'] = False
            context['is_expired_test'] = False
            
            if details.start_datetime and details.start_datetime > now:
                context['is_future_test'] = True
            
            if details.end_datetime and details.end_datetime < now:
                context['is_expired_test'] = True
        
        # 5. Related Items (Same Category)
        related_items = MarketplaceItem.objects.filter(
            categories__in=item.categories.all(),
            is_active=True
        ).exclude(id=item.id).distinct()[:3]
        
        context['related_items'] = related_items

        return context