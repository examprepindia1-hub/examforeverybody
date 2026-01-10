from django.contrib import admin
from .models import CourseAttributes, CourseModule, CourseLesson

class CourseLessonInline(admin.StackedInline):
    model = CourseLesson
    extra = 1

@admin.register(CourseModule)
class CourseModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'course__item__title')
    inlines = [CourseLessonInline]
    ordering = ('course', 'order')

class CourseModuleInline(admin.StackedInline):
    model = CourseModule
    extra = 1
    show_change_link = True # Allow clicking through to edit module details

@admin.register(CourseAttributes)
class CourseAttributesAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'course_level', 'item')
    search_fields = ('item__title',)
    inlines = [CourseModuleInline]

# We also register CourseLesson separately for detailed editing if needed
@admin.register(CourseLesson)
class CourseLessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'duration_minutes', 'is_preview', 'order')
    list_filter = ('module__course', 'is_preview')
    search_fields = ('title', 'module__title')
