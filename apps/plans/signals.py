from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.orders.models import Order
from .models import PlanAssignment
from .services import recalc_assignment_progress


@receiver(post_save, sender=Order)
def order_post_save_handler(sender, instance, created, **kwargs):
    """
    При изменении заказа — пересчитываем прогресс менеджера по активным планам.
    Оптимизируем: выбираем только назначения, чьи периоды включают дату заказа.
    """
    if not instance.responsible:
        return
    
    manager = instance.responsible
    order_date = instance.created_at.date()
    
    # Находим активные назначения, для которых дата заказа в периоде
    assignments = PlanAssignment.objects.filter(
        manager=manager,
        plan__start_date__lte=order_date,
        plan__end_date__gte=order_date
    )
    
    for assignment in assignments:
        recalc_assignment_progress(assignment)


@receiver(post_delete, sender=Order)
def order_post_delete_handler(sender, instance, **kwargs):
    """
    При удалении заказа — пересчитываем прогресс менеджера по активным планам.
    """
    if not instance.responsible:
        return
    
    manager = instance.responsible
    order_date = instance.created_at.date()
    
    assignments = PlanAssignment.objects.filter(
        manager=manager,
        plan__start_date__lte=order_date,
        plan__end_date__gte=order_date
    )
    
    for assignment in assignments:
        recalc_assignment_progress(assignment)

