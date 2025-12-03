from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('marketplace/', include('marketplace.urls')),
    path('accounts/', include('users.urls')),
    path('billing/', include('billing.urls')),
    path('test/', include('mocktests.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)