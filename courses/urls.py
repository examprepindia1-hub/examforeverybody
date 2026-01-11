from django.urls import path
from .views import CoursePlayerView, ToggleLessonCompletionView

app_name = 'courses'

urlpatterns = [
    path('<slug:slug>/learn/', CoursePlayerView.as_view(), name='course_player'),
    path('api/toggle-lesson/', ToggleLessonCompletionView.as_view(), name='toggle_lesson_completion'),
]
