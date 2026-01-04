from django.contrib import sitemaps
from django.urls import reverse
from blog.models import Post
from marketplace.models import MarketplaceItem

# 1. STATIC PAGES (Home, About, Contact, etc.)
class StaticViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        # These are the 'name=' values from your core/urls.py
        return [
            'home', 
            'about_us', 
            'contact_support', 
            'careers', 
            'faq', 
            'privacy_policy', 
            'terms_of_service',
            'cookie_policy'
        ]

    def location(self, item):
        return reverse(item)

# 2. BLOG POSTS SITEMAP
class BlogSitemap(sitemaps.Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        # Only show published posts
        return Post.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

# 3. MARKETPLACE ITEMS SITEMAP (Mock Tests, Workshops)
class MarketplaceSitemap(sitemaps.Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        # Only show active items
        return MarketplaceItem.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.modified  # Using TimeStampedModel's 'modified' field