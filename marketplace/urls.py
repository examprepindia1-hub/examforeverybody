# marketplace/urls.py
from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # This will match /marketplace/some-course-slug/
    path('<slug:slug>/', views.ItemDetailView.as_view(), name='item_detail'),
    path('', views.ItemListView.as_view(), name='item_list'),
]