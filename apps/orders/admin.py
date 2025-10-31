from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Инлайн для позиций заказа"""
    model = OrderItem
    extra = 1
    fields = (
        'product', 'product_code', 'product_name',
        'quantity', 'price', 'amount', 'segment', 'branch_city'
    )
    readonly_fields = (
        'product_code', 'product_name', 'price',
        'segment', 'branch_city', 'amount'
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админка для заказов"""
    list_display = (
        'order_number', 'created_at', 'client', 'status',
        'price_level', 'total_amount', 'responsible'
    )
    list_filter = (
        'status', 'source', 'payment_method', 'price_level', 'created_at'
    )
    search_fields = (
        'order_number', 'client__name', 'sale_number'
    )
    readonly_fields = (
        'order_number', 'created_at', 'created_by',
        'updated_at', 'updated_by', 'total_amount'
    )
    inlines = [OrderItemInline]

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'order_number', 'created_at', 'created_by',
                'updated_at', 'updated_by'
            )
        }),
        ('Клиент и ответственный', {
            'fields': ('client', 'responsible', 'status')
        }),
        ('Параметры заказа', {
            'fields': (
                'source', 'payment_method', 'delivery_method', 'price_level'
            )
        }),
        ('Дополнительно', {
            'fields': ('is_promo', 'sale_number', 'notes', 'total_amount')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Админка для позиций заказов"""
    list_display = (
        'order', 'product_code', 'product_name',
        'quantity', 'price', 'amount'
    )
    list_filter = ('order__created_at', 'segment')
    search_fields = ('product_name', 'product_code', 'order__order_number')
    readonly_fields = (
        'product_code', 'product_name', 'price',
        'segment', 'branch_city', 'amount'
    )
