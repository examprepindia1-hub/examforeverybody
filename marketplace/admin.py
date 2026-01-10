from django.contrib import admin
from core.models import Category
from .models import MarketplaceItem, Testimonial
# Import Course and Workshop attributes
from courses.models import CourseAttributes
from workshops.models import WorkshopAttributes

class CourseAttributesInline(admin.StackedInline):
    model = CourseAttributes
    can_delete = False
    verbose_name_plural = 'Video Course Details'

class WorkshopAttributesInline(admin.StackedInline):
    model = WorkshopAttributes
    can_delete = False
    verbose_name_plural = 'Workshop Details'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'value', 'parent_category')
    search_fields = ['display_name', 'value'] 
    # Removed prepopulated_fields as Category has no slug

@admin.register(MarketplaceItem)
class MarketplaceItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'price', 'is_active', 'created', 'slug')
    list_filter = ('item_type', 'is_active', 'categories')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['categories']
    inlines = [CourseAttributesInline, WorkshopAttributesInline]

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'rating', 'created')
    list_filter = ('rating', 'item')