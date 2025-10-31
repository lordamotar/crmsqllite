from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Role, Position, Branch


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at')


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at')


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'city', 'created_at')
    search_fields = ('name', 'city', 'address', 'phone')
    readonly_fields = ('id', 'created_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email', 'short_name', 'role', 'position', 'branch', 
        'manager', 'is_active', 'created_at'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'role', 
        'position', 'branch', 'created_at'
    )
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Личная информация', {
            'fields': ('first_name', 'last_name', 'middle_name', 'phone', 'avatar', 'bio')
        }),
        ('Организационная структура', {
            'fields': ('role', 'position', 'branch', 'manager')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )

    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def short_name(self, obj):
        return obj.short_name
    short_name.short_description = 'Имя'