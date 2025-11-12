from django.contrib import admin
from .models import WorkSession, DutyAssignment


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_time', 'end_time', 'is_closed')
    list_filter = ('is_closed', 'start_time')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')


@admin.register(DutyAssignment)
class DutyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'manager', 'created_by', 'created_at')
    list_filter = ('date',)
    search_fields = ('manager__username', 'manager__first_name', 'manager__last_name')

