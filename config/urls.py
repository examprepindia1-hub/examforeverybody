from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap, BlogSitemap, MarketplaceSitemap
from core.views import robots_txt

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogSitemap,
    'marketplace': MarketplaceSitemap,
}

urlpatterns = [
    path('e4e/management/console', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('marketplace/', include('marketplace.urls')),
    path('accounts/', include('users.urls')),
    path('billing/', include('billing.urls')),
    path('test/', include('mocktests.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('blog/', include('blog.urls', namespace='blog')),
    path('paypal/', include('paypal.standard.ipn.urls')),
    path('accounts/', include('allauth.urls')),
    path('courses/', include('courses.urls', namespace='courses')),
    path('certificates/', include('certificates.urls', namespace='certificates')),
    path('workshops/', include('workshops.urls', namespace='workshops')),
    path('', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)