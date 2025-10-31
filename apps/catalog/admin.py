from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Segment, BranchCity, OrderSource, PaymentMethod, OrderStatus,
    ProductSegment, ClientCity
)


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(BranchCity)
class BranchCityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(OrderSource)
class OrderSourceAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display']
    search_fields = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="color: {};">●</span> {}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Цвет'


@admin.register(ProductSegment)
class ProductSegmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(ClientCity)
class ClientCityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']