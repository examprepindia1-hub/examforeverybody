from django.urls import path
from . import views

urlpatterns = [
    path('start/<slug:slug>/', views.start_test, name='start_test'),
    path('attempt/<int:attempt_id>/', views.take_test, name='take_test'),
    path('api/save-answer/', views.save_answer, name='save_answer'),
    path('submit/<int:attempt_id>/', views.submit_test, name='submit_test'),
    path('api/report-question/', views.report_question, name='report_question'),
]