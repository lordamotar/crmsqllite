from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from django.utils.safestring import mark_safe
import json
from datetime import timedelta
from apps.orders.models import Order
from apps.clients.models import Client
from apps.products.models import Product
from apps.cities.models import City

PERIODS = {
    '1day': timedelta(days=1),
    '7days': timedelta(days=7),
    '1month': timedelta(days=30),
    'quarter': timedelta(days=91),
    'halfyear': timedelta(days=182),
    'year': timedelta(days=365),
}


@login_required(login_url='login')
def dashboard_view(request):
    """Главная страница dashboard с реальными метриками"""
    period_key = request.GET.get('period', '1day')
    delta = PERIODS.get(period_key, PERIODS['1day'])
    since = timezone.now() - delta

    # Метрики за период
    orders_qs = Order.objects.filter(created_at__gte=since)
    revenue = orders_qs.aggregate(s=Sum('total_amount'))['s'] or 0
    orders_count = orders_qs.count()

    # Новые клиенты за период
    clients_count = Client.objects.filter(created_at__gte=since).count()

    # Общие справочники (не зависят от периода)
    products_count = Product.objects.count()
    cities_count = City.objects.count()

    # Данные по статусам заказов для диаграммы (все заказы, не только за период)
    status_data = Order.objects.values('status').annotate(count=Count('id')).order_by('status')
    status_labels = []
    status_values = []
    status_colors = {
        'new': '#696cff',  # primary
        'new_paid': '#696cff',  # primary
        'reserve': '#71dd37',  # success
        'transfer': '#03c3ec',  # info
        'delivery': '#ffab00',  # warning
        'callback': '#ff3e1d',  # danger
        'completed': '#71dd37',  # success
        'refund': '#ff3e1d',  # danger
        'cancelled': '#8592a3',  # secondary
    }
    
    colors = []
    for item in status_data:
        status_labels.append(item['status'])
        status_values.append(item['count'])
        colors.append(status_colors.get(item['status'], '#8592a3'))
    
    # Отладочная информация
    print(f"Status data: {list(status_data)}")
    print(f"Status labels: {status_labels}")
    print(f"Status values: {status_values}")
    print(f"Colors: {colors}")

    # Последние заказы для активности
    recent_orders = Order.objects.select_related(
        'client'
    ).order_by('-created_at')[:5]
    recent_clients = Client.objects.order_by('-created_at')[:5]

    context = {
        'title': 'Главная страница',
        'revenue': revenue,
        'orders_count': orders_count,
        'clients_count': clients_count,
        'products_count': products_count,
        'cities_count': cities_count,
        'active_period': period_key,
        'recent_orders': recent_orders,
        'recent_clients': recent_clients,
        'status_labels': mark_safe(json.dumps(status_labels)),
        'status_values': mark_safe(json.dumps(status_values)),
        'status_colors': mark_safe(json.dumps(colors)),
    }
    return render(request, 'dashboard/dashboard.html', context)