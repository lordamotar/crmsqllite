from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'language', 'currency', 'theme', 'created_at']
    list_filter = ['language', 'currency', 'theme', 'email_notifications', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email', 'bio']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
