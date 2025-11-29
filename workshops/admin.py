from django.contrib import admin
from .models import WorkshopAttributes, WorkshopSession, WorkshopAttendee

class WorkshopSessionInline(admin.TabularInline):
    model = WorkshopSession
    extra = 1

@admin.register(WorkshopAttributes)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('item', 'instructor', 'total_duration_hours')
    # Removed 'language' and 'level' as they don't exist in your model
    search_fields = ('item__title',)
    inlines = [WorkshopSessionInline]

@admin.register(WorkshopSession)
class WorkshopSessionAdmin(admin.ModelAdmin):
    list_display = ('workshop', 'start_time', 'end_time', 'current_enrolled_count')
    list_filter = ('start_time',)