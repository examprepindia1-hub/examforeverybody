from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

urlpatterns = [
    # --- Authentication (Handled by Allauth now) ---
    # Redirect legacy profile view if needed or keep it for user updates
    path('profile/', views.profile, name='profile'),
]