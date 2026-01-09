from django.urls import include, path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.home, name='home'),  
    path('dashboard/', views.dashboard_view, name='dashboard'),          # Smart Switch
    path('dashboard/recent-attempts/', views.dashboard_recent_attempt_view, name='dashboard_recent_attempts'), # Explicit Dashboard link
    path('explore/', views.explore, name='explore'),
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'), # Explicit Catalog link
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('leaderboard/<slug:slug>/', views.leaderboard, name='leaderboard_slug'),
    path('contact/', views.contact_support, name='contact_support'),
    path('about/', views.about_us, name='about_us'),
    path('careers/', views.careers, name='careers'),
    path('faq/', views.faq, name='faq'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)