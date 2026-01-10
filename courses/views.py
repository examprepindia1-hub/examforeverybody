from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from .models import CourseAttributes, CourseLesson

class CoursePlayerView(LoginRequiredMixin, DetailView):
    model = MarketplaceItem
    template_name = 'courses/course_player.html'
    context_object_name = 'item'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def dispatch(self, request, *args, **kwargs):
        # 1. Get the item
        self.object = self.get_object()
        
        # 2. Check Enrollment
        is_enrolled = UserEnrollment.objects.filter(
            user=request.user, 
            item=self.object,
            is_active=True
        ).exists()
        
        if not is_enrolled:
            messages.error(request, "You must enroll in this course to access the content.")
            return redirect('marketplace:item_detail', slug=self.object.slug)
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get Course Attributes
        try:
            course = self.object.course_details
        except CourseAttributes.DoesNotExist:
            # Fallback if data is missing
            course = None
            
        context['course'] = course
        
        # Determine Current Lesson
        lesson_id = self.request.GET.get('lesson')
        current_lesson = None
        
        if course:
            modules = course.modules.prefetch_related('lessons').all()
            context['modules'] = modules
            
            if lesson_id:
                current_lesson = get_object_or_404(CourseLesson, id=lesson_id, module__course=course)
            else:
                # Default to first lesson of first module
                first_module = modules.first()
                if first_module:
                    current_lesson = first_module.lessons.first()
        
        context['current_lesson'] = current_lesson
        
        return context
