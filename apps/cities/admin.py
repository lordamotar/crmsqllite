from django.contrib import admin
from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'country', 'is_active', 'created_at')
    list_filter = ('is_active', 'country', 'region')
    search_fields = ('name', 'region')
    ordering = ('name',)