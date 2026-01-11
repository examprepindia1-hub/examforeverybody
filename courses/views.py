from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from django.views import View
from django.http import JsonResponse
import json
from .models import CourseAttributes, CourseLesson, UserCourseProgress, UserLessonCompletion

class ToggleLessonCompletionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        
        lesson = get_object_or_404(CourseLesson, id=lesson_id)
        
        # 1. Toggle Lesson Completion
        completion, created = UserLessonCompletion.objects.get_or_create(user=request.user, lesson=lesson)
        
        if not created:
            # If it existed, delete it (Un-complete)
            completion.delete()
            is_completed = False
        else:
            is_completed = True
            
        # 2. Recalculate Course Progress
        course = lesson.module.course
        total_lessons = CourseLesson.objects.filter(module__course=course).count()
        completed_lessons = UserLessonCompletion.objects.filter(
            user=request.user, 
            lesson__module__course=course
        ).count()
        
        percent = 0.0
        if total_lessons > 0:
            percent = (completed_lessons / total_lessons) * 100
            
        # 3. Update/Create Progress Record
        progress, _ = UserCourseProgress.objects.get_or_create(user=request.user, course=course)
        progress.percent_complete = round(percent, 2)
        
        # Mark as fully complete if 100%
        if percent >= 100:
            progress.is_completed = True
        else:
            progress.is_completed = False
            
        progress.save()
        
        return JsonResponse({
            'status': 'success',
            'is_completed': is_completed,
            'percent_complete': progress.percent_complete
        })

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

            # --- PROGRESS TRACKING INJECTION ---
            # 1. Get Set of Completed Lesson IDs for Sidebar Checkmarks
            completed_ids = UserLessonCompletion.objects.filter(
                user=self.request.user,
                lesson__module__course=course
            ).values_list('lesson_id', flat=True)
            context['completed_lesson_ids'] = set(completed_ids)
            
            # 2. Get Overall Progress
            progress = UserCourseProgress.objects.filter(user=self.request.user, course=course).first()
            context['percent_complete'] = progress.percent_complete if progress else 0
            
            # 3. Check if CURRENT lesson is complete
            context['is_current_lesson_complete'] = current_lesson.id in context['completed_lesson_ids'] if current_lesson else False

        context['current_lesson'] = current_lesson
        
        return context
