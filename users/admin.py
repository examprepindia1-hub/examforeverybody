from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'country', 'is_staff')
    list_filter = ('role', 'country', 'is_staff', 'is_active')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'country')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'country')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)