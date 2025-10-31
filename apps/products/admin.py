from django.contrib import admin
from .models import Product, ProductGroup, Branch, Warehouse


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    """Админка для групп товаров"""
    list_display = ('code', 'name', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Админка для товаров"""
    list_display = (
        'code', 'name', 'price', 'wholesale_price', 'promotional_price', 'retail_price',
        'segment', 'tire_type', 'seasonality', 'product_group', 'is_active'
    )
    list_filter = (
        'segment', 'tire_type', 'seasonality', 'product_group',
        'branch_city', 'is_active', 'created_at'
    )
    search_fields = ('code', 'name', 'description', 'dimension')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Цены', {
            'fields': ('price', 'wholesale_price', 'promotional_price', 'retail_price')
        }),
        ('Характеристики товара', {
            'fields': (
                'sales_plan_selection', 'dimension', 'tire_type',
                'seasonality', 'assortment_group'
            )
        }),
        ('Классификация', {
            'fields': ('segment', 'product_group')
        }),
        ('Расположение', {
            'fields': ('branch_city', 'branch', 'warehouse')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    """Админка для филиалов"""
    list_display = ('name', 'city', 'is_active')
    list_filter = ('city', 'is_active')
    search_fields = ('name', 'city__name')


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    """Админка для складов"""
    list_display = ('name', 'branch', 'is_active')
    list_filter = ('branch__city', 'branch', 'is_active')
    search_fields = ('name', 'branch__name', 'branch__city__name')
