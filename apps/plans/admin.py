from django.contrib import admin
from .models import Plan, PlanAssignment


class PlanAssignmentInline(admin.TabularInline):
    """Inline для назначений плана"""
    model = PlanAssignment
    extra = 0
    readonly_fields = ('achieved_count', 'achieved_sum', 'is_achieved', 'created_at', 'updated_at')
    fields = (
        'manager', 'target_count', 'target_sum', 'criteria_operator',
        'achieved_count', 'achieved_sum', 'is_achieved'
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Админ-панель для планов"""
    list_display = ('name', 'start_date', 'end_date', 'created_by', 'created_at')
    list_filter = ('start_date', 'end_date', 'created_at')
    search_fields = ('name', 'description', 'created_by__first_name', 'created_by__last_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlanAssignmentInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Период', {
            'fields': ('start_date', 'end_date')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlanAssignment)
class PlanAssignmentAdmin(admin.ModelAdmin):
    """Админ-панель для назначений планов"""
    list_display = (
        'plan', 'manager', 'target_count', 'target_sum',
        'achieved_count', 'achieved_sum', 'is_achieved'
    )
    list_filter = ('is_achieved', 'criteria_operator', 'created_at')
    search_fields = (
        'plan__name', 'manager__first_name', 'manager__last_name'
    )
    readonly_fields = ('achieved_count', 'achieved_sum', 'is_achieved', 'created_at', 'updated_at')

