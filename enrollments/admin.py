from django.contrib import admin
from .models import UserEnrollment

@admin.register(UserEnrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    # 'created' comes from TimeStampedModel
    list_display = ('user', 'item', 'created', 'is_active')
    list_filter = ('is_active', 'created')
    search_fields = ('user__email', 'item__title')
    autocomplete_fields = ['user', 'item']