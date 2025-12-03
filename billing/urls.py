from django.urls import path
from . import views

urlpatterns = [
    path('history/', views.order_history, name='order_history'),
    path('buy/<slug:slug>/', views.initiate_purchase, name='initiate_purchase'),
    
]