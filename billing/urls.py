from django.urls import path
from . import views

urlpatterns = [
    path('buy/<slug:slug>/', views.initiate_purchase, name='initiate_purchase'),
]