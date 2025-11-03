from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from decimal import Decimal
import json
from datetime import timedelta, date
from apps.orders.models import Order
from apps.clients.models import Client
from apps.products.models import Product
from apps.cities.models import City
from apps.plans.models import PlanAssignment

PERIODS = {
    '1day': timedelta(days=1),
    '7days': timedelta(days=7),
    '1month': timedelta(days=30),
    'quarter': timedelta(days=91),
    'halfyear': timedelta(days=182),
    'year': timedelta(days=365),
}


@login_required(login_url='accounts:login')
def dashboard_view(request):
    """Главная страница dashboard с реальными метриками"""
    period_key = request.GET.get('period', '1day')
    # Поддержка пользовательского периода через GET start/end (YYYY-MM-DD)
    start_param = request.GET.get('start')
    end_param = request.GET.get('end')

    start_date = None
    end_date = None
    if start_param and end_param:
        try:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)
        except Exception:
            start_date = None
            end_date = None

    if start_date and end_date and start_date <= end_date:
        # Пользовательский диапазон дат
        since = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()))
        until = timezone.make_aware(timezone.datetime.combine(end_date, timezone.datetime.max.time()))
        use_custom_range = True
    else:
        # Если параметр period НЕ передан вовсе — по умолчанию текущий месяц
        if 'period' not in request.GET:
            tz_now = timezone.now()
            month_start = timezone.make_aware(timezone.datetime(tz_now.year, tz_now.month, 1))
            since = month_start
            until = tz_now
            use_custom_range = True
            period_key = 'custom'
        else:
            # Предустановленные периоды
            delta = PERIODS.get(period_key, PERIODS['1day'])
            since = timezone.now() - delta
            until = timezone.now()
            use_custom_range = False

    # Определяем фильтр заказов по роли пользователя
    user = request.user
    # Если суперпользователь - видит все заказы
    if user.is_superuser:
        responsible_users = None  # None означает все пользователи
    else:
        # Получаем подчиненных пользователя
        subordinates = user.get_subordinates()
        # Если есть подчиненные (начальник отдела) - свои + подчиненные
        # Если нет подчиненных (менеджер) - только свои
        if subordinates.exists():
            responsible_users = [user] + list(subordinates)
        else:
            responsible_users = [user]

    # Фильтр для заказов по ответственным
    if responsible_users is None:
        # Суперпользователь - все заказы
        order_filter = {}
    else:
        # Фильтруем по ответственным (менеджер или начальник + подчиненные)
        order_filter = {'responsible__in': responsible_users}

    # Метрики за период
    orders_qs = Order.objects.filter(created_at__gte=since, created_at__lte=until, **order_filter)
    revenue = orders_qs.aggregate(s=Sum('total_amount'))['s'] or 0
    orders_count = orders_qs.count()

    # Новые клиенты за период
    clients_count = Client.objects.filter(created_at__gte=since, created_at__lte=until).count()

    # Общие справочники (не зависят от периода)
    products_count = Product.objects.count()
    cities_count = City.objects.count()

    # Данные по статусам заказов для диаграммы (с учетом фильтра по роли)
    # Группируем причины отмены в один статус "Отмененные"
    cancel_reasons = [
        'cancel_no_answer',
        'cancel_not_suitable_year',
        'cancel_wrong_order',
        'cancel_found_other',
        'cancel_delivery_terms',
        'cancel_no_quantity',
        'cancel_incomplete',
    ]
    
    # Получаем все статусы с учетом фильтра
    status_data_raw = Order.objects.filter(**order_filter).values('status').annotate(count=Count('id')).order_by('status')
    
    # Группируем данные: причины отмены объединяем в "cancelled"
    status_counts = {}
    cancelled_count = 0
    
    for item in status_data_raw:
        status = item['status']
        count = item['count']
        
        if status == 'cancelled':
            cancelled_count += count
        elif status in cancel_reasons:
            cancelled_count += count
        else:
            status_counts[status] = count
    
    # Добавляем объединённый статус отмены, если есть отменённые заказы
    if cancelled_count > 0:
        status_counts['cancelled'] = cancelled_count
    
    # Формируем списки для диаграммы
    status_labels = []
    status_values = []
    status_labels_display = []
    
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
    
    status_names = {
        'new': 'Новые',
        'new_paid': 'Новые оплаченные',
        'reserve': 'Резерв',
        'transfer': 'Перемещение',
        'delivery': 'Доставка',
        'callback': 'Перезвонить',
        'completed': 'Выполненные',
        'refund': 'Возврат',
        'cancelled': 'Отмененные',
    }
    
    colors = []
    # Сортируем статусы для корректного отображения
    sorted_statuses = sorted(status_counts.items(), key=lambda x: status_names.get(x[0], x[0]))
    
    for status, count in sorted_statuses:
        status_labels.append(status)
        status_values.append(count)
        status_labels_display.append(status_names.get(status, status))
        colors.append(status_colors.get(status, '#8592a3'))

    # Последние заказы для активности (с учетом фильтра)
    recent_orders = Order.objects.filter(**order_filter).select_related(
        'client'
    ).order_by('-created_at')[:5]
    recent_clients = Client.objects.order_by('-created_at')[:5]

    # Информация о плане (заказы)
    # Список статусов отмены
    cancelled_statuses = [
        Order.STATUS_CANCELLED,
        Order.STATUS_CANCEL_NO_ANSWER,
        Order.STATUS_CANCEL_NOT_SUITABLE_YEAR,
        Order.STATUS_CANCEL_WRONG_ORDER,
        Order.STATUS_CANCEL_FOUND_OTHER,
        Order.STATUS_CANCEL_DELIVERY_TERMS,
        Order.STATUS_CANCEL_NO_QUANTITY,
        Order.STATUS_CANCEL_INCOMPLETE,
    ]
    
    # Все заказы за период (все созданные пользователем заказы, включая отмененные)
    all_orders = Order.objects.filter(
        created_at__gte=since,
        created_at__lte=until,
        **order_filter
    )
    
    total_orders_count = all_orders.count()
    total_orders_sum = all_orders.aggregate(s=Sum('total_amount'))['s'] or 0
    
    # Выполненные заказы (без отмененных)
    completed_orders = all_orders.filter(status=Order.STATUS_COMPLETED)
    completed_count = completed_orders.count()
    completed_sum = completed_orders.aggregate(s=Sum('total_amount'))['s'] or 0
    
    # Отмененные заказы (все причины отмены)
    cancelled_orders = all_orders.filter(status__in=cancelled_statuses)
    cancelled_count = cancelled_orders.count()
    cancelled_sum = cancelled_orders.aggregate(s=Sum('total_amount'))['s'] or 0
    
    # Осталось (активные заказы - не выполненные и не отмененные)
    excluded_statuses = [Order.STATUS_COMPLETED] + cancelled_statuses
    active_orders = all_orders.exclude(status__in=excluded_statuses)
    active_count = active_orders.count()
    active_sum = active_orders.aggregate(s=Sum('total_amount'))['s'] or 0

    # Прогресс плана за ТЕКУЩИЙ МЕСЯЦ (независимо от выбранного фильтра периода)
    plan_progress = None
    tz_now = timezone.now()
    month_start = date(tz_now.year, tz_now.month, 1)
    # вычисляем конец месяца
    if tz_now.month == 12:
        next_month = date(tz_now.year + 1, 1, 1)
    else:
        next_month = date(tz_now.year, tz_now.month + 1, 1)
    month_end = next_month - timezone.timedelta(days=1)

    # Плановые назначения, перекрывающие текущий месяц
    assignments_qs = PlanAssignment.objects.filter(
        plan__start_date__lte=month_end,
        plan__end_date__gte=month_start,
    )
    if responsible_users is not None:
        assignments_qs = assignments_qs.filter(manager__in=responsible_users)

    total_target = assignments_qs.aggregate(total=Sum('target_count'))['total'] or 0

    # Выполнено (только completed) в текущем месяце, по соответствующим ответственным
    completed_month_qs = Order.objects.filter(
        created_at__date__gte=month_start,
        created_at__date__lte=month_end,
        status=Order.STATUS_COMPLETED,
        **({} if responsible_users is None else {'responsible__in': responsible_users})
    )
    completed_month = completed_month_qs.count()

    if total_target > 0:
        progress_percent = min(100, round((completed_month / total_target) * 100, 2))
        remaining = max(0, total_target - completed_month)
        is_plan_completed = completed_month >= total_target
        plan_progress = {
            'plan_count': int(total_target),
            'completed': int(completed_month),
            'remaining': int(remaining),
            'progress_percent': progress_percent,
            'is_completed': is_plan_completed,
            'plan_name': 'План (текущий месяц)',
            'plan_period': f"{month_start.strftime('%d.%m.%Y')} - {month_end.strftime('%d.%m.%Y')}",
        }

    context = {
        'title': 'Главная страница',
        'revenue': revenue,
        'orders_count': orders_count,
        'clients_count': clients_count,
        'products_count': products_count,
        'cities_count': cities_count,
        'active_period': period_key,
        'start': start_param or (start_date.isoformat() if start_date else ''),
        'end': end_param or (end_date.isoformat() if end_date else ''),
        'recent_orders': recent_orders,
        'recent_clients': recent_clients,
        'status_labels': mark_safe(json.dumps(status_labels)),
        'status_values': mark_safe(json.dumps(status_values)),
        'status_colors': mark_safe(json.dumps(colors)),
        'status_labels_display': mark_safe(json.dumps(status_labels_display)),
        # Информация о плане
        'total_orders_count': total_orders_count,
        'total_orders_sum': total_orders_sum,
        'completed_count': completed_count,
        'completed_sum': completed_sum,
        'cancelled_count': cancelled_count,
        'cancelled_sum': cancelled_sum,
        'active_count': active_count,
        'active_sum': active_sum,
        # Прогресс выполнения плана
        'plan_progress': plan_progress,
    }
    return render(request, 'dashboard/dashboard.html', context)