from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.home, name='home'),            # Smart Switch
    path('dashboard/', views.dashboard_view, name='dashboard'), # Explicit Dashboard link
    path('explore/', views.explore, name='explore'), # Explicit Catalog link
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)