from django.urls import path
from . import views

urlpatterns = [
    # ... existing paths ...
    path('history/', views.order_history, name='order_history'),
    path('buy/<slug:slug>/', views.initiate_purchase, name='initiate_purchase'),
    
    # API Endpoints
    path('api/create-paypal-order/', views.create_paypal_order, name='create_paypal_order'),
    path('api/capture-paypal-order/', views.capture_paypal_order, name='capture_paypal_order'),
    path('api/create-upi-order/', views.create_upi_order, name='create_upi_order'),
    
    # NEW: Status Polling & Timeout
    path('api/check-status/<str:order_id>/', views.check_payment_status, name='check_payment_status'),
    path('api/expire-order/<str:order_id>/', views.expire_order, name='expire_order'),
]