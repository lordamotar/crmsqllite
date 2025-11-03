from django.db.models import Sum, Count, Q
from datetime import date

from apps.orders.models import Order


def calculate_manager_progress(manager, start_date, end_date, status_include=None):
    """
    Считает количество и сумму заказов менеджера за период.
    status_include — список статусов заказов, которые считать.
    Если None — считать все заказы кроме отменённых.
    """
    qs = Order.objects.filter(
        responsible=manager,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    # Исключаем отменённые заказы по умолчанию
    if status_include is None:
        excluded_statuses = [
            Order.STATUS_CANCELLED,
            Order.STATUS_CANCEL_NO_ANSWER,
            Order.STATUS_CANCEL_NOT_SUITABLE_YEAR,
            Order.STATUS_CANCEL_WRONG_ORDER,
            Order.STATUS_CANCEL_FOUND_OTHER,
            Order.STATUS_CANCEL_DELIVERY_TERMS,
            Order.STATUS_CANCEL_NO_QUANTITY,
            Order.STATUS_CANCEL_INCOMPLETE,
            Order.STATUS_REFUND,
        ]
        qs = qs.exclude(status__in=excluded_statuses)
    else:
        qs = qs.filter(status__in=status_include)
    
    agg = qs.aggregate(
        total_sum=Sum('total_amount'),
        total_count=Count('id')
    )
    total_sum = agg['total_sum'] or 0
    total_count = agg['total_count'] or 0
    return int(total_count), total_sum


def recalc_assignment_progress(assignment):
    """
    Пересчитать прогресс по конкретному PlanAssignment —
    обновить achieved_* и is_achieved.
    План считается выполненным, если количество заказов со статусом 'completed'
    равно целевому количеству (target_count).
    """
    start = assignment.plan.start_date
    end = assignment.plan.end_date
    
    # Считаем только заказы со статусом 'completed'
    completed_count, completed_sum = calculate_manager_progress(
        assignment.manager, 
        start, 
        end, 
        status_include=[Order.STATUS_COMPLETED]
    )
    
    assignment.achieved_count = completed_count
    assignment.achieved_sum = completed_sum
    # План выполнен, если количество completed заказов >= target_count
    assignment.is_achieved = (completed_count >= assignment.target_count)
    assignment.save(update_fields=['achieved_count', 'achieved_sum', 'is_achieved'])
    
    return assignment


def recalc_plan_progress(plan):
    """
    Пересчитать прогресс всех назначений плана.
    Оптимизированная версия с массовым обновлением.
    План считается выполненным, если количество заказов со статусом 'completed'
    равно или превышает целевое количество (target_count).
    """
    from django.db.models import Sum, Count
    
    # Получаем агрегацию по менеджерам за период плана
    # Считаем только заказы со статусом 'completed'
    orders_qs = Order.objects.filter(
        created_at__date__gte=plan.start_date,
        created_at__date__lte=plan.end_date,
        status=Order.STATUS_COMPLETED
    )
    
    # Агрегируем по менеджерам
    progress_by_manager = orders_qs.values('responsible').annotate(
        total_sum=Sum('total_amount'),
        total_count=Count('id')
    )
    
    # Обновляем назначения
    updated = []
    for assignment in plan.assignments.all():
        # Находим прогресс для этого менеджера
        manager_progress = next(
            (p for p in progress_by_manager if p['responsible'] == assignment.manager_id),
            None
        )
        
        if manager_progress:
            assignment.achieved_count = manager_progress['total_count'] or 0
            assignment.achieved_sum = manager_progress['total_sum'] or 0
        else:
            assignment.achieved_count = 0
            assignment.achieved_sum = 0
        
        # План выполнен, если количество completed заказов >= target_count
        assignment.is_achieved = (assignment.achieved_count >= assignment.target_count)
        assignment.save(update_fields=['achieved_count', 'achieved_sum', 'is_achieved'])
        updated.append(assignment)
    
    return updated

