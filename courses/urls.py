from django.urls import path
from .views import CoursePlayerView

app_name = 'courses'

urlpatterns = [
    path('<slug:slug>/learn/', CoursePlayerView.as_view(), name='course_player'),
]
