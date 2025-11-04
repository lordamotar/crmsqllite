from datetime import datetime
from django.utils import timezone
from typing import Iterable

from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps.orders.models import Order, OrderItem


# Единая группа отмен — сводим все детальные причины в одну «cancelled»
CANCEL_STATUSES = {
    Order.STATUS_REFUND,
    Order.STATUS_CANCEL_NO_ANSWER,
    Order.STATUS_CANCEL_NOT_SUITABLE_YEAR,
    Order.STATUS_CANCEL_WRONG_ORDER,
    Order.STATUS_CANCEL_FOUND_OTHER,
    Order.STATUS_CANCEL_DELIVERY_TERMS,
    Order.STATUS_CANCEL_NO_QUANTITY,
    Order.STATUS_CANCEL_INCOMPLETE,
}


def parse_date(param: str):
    return datetime.strptime(param, "%Y-%m-%d").date()


def resolve_period(request):
    """Возвращает (start_date, end_date). По умолчанию — текущий месяц."""
    start_param = request.query_params.get("start")
    end_param = request.query_params.get("end")

    if start_param and end_param:
        return parse_date(start_param), parse_date(end_param)

    today = timezone.now().date()
    # end по умолчанию — сегодня, start — первый день месяца end
    end = parse_date(end_param) if end_param else today
    start = parse_date(start_param) if start_param else end.replace(day=1)
    return start, end


def apply_optional_filters(orders_qs, request, user):
    """Применяет необязательные фильтры: source, statuses, manager, с учётом прав."""
    source = request.query_params.get("source")
    if source:
        orders_qs = orders_qs.filter(source=source)

    statuses = request.query_params.get("statuses") or request.query_params.get("status")
    if statuses:
        raw = [s.strip() for s in statuses.split(',') if s.strip()]
        expanded = []
        for s in raw:
            if s == Order.STATUS_CANCELLED:
                expanded.extend(list(CANCEL_STATUSES))
            else:
                expanded.append(s)
        orders_qs = orders_qs.filter(status__in=expanded)

    manager_id = request.query_params.get("manager")
    if manager_id:
        try:
            mid = int(manager_id)
        except ValueError:
            mid = None
        if mid:
            # ограничиваем выбор менеджера рамками доступности
            allowed_qs = role_scoped_orders(user, orders_qs.earliest("created_at").created_at.date(), orders_qs.latest("created_at").created_at.date())
            # Если менеджер в зоне видимости — применим фильтр
            if allowed_qs.filter(responsible_id=mid).exists():
                orders_qs = orders_qs.filter(responsible_id=mid)
    return orders_qs


def role_scoped_orders(user, start, end):
    qs = Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
    if getattr(user, "is_superuser", False):
        return qs
    # начальник отдела: свои + подчиненные
    if hasattr(user, "get_subordinates"):
        subordinates = user.get_subordinates()
        return qs.filter(Q(responsible=user) | Q(responsible__in=subordinates))
    # менеджер: только свои
    return qs.filter(responsible=user)


@method_decorator(cache_page(60), name='get')
class OverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = resolve_period(request)
        orders = role_scoped_orders(request.user, start, end)
        orders = apply_optional_filters(orders, request, request.user)

        total_orders = orders.count()
        completed = orders.filter(status=Order.STATUS_COMPLETED)
        cancelled = orders.filter(status__in=CANCEL_STATUSES)

        data = {
            "orders_total": total_orders,
            "orders_completed": completed.count(),
            "orders_cancelled": cancelled.count(),
            "sum_total": int(orders.aggregate(s=Sum("total_amount"))["s"] or 0),
            "sum_completed": int(completed.aggregate(s=Sum("total_amount"))["s"] or 0),
            "sum_cancelled": int(cancelled.aggregate(s=Sum("total_amount"))["s"] or 0),
        }
        return Response(data)


@method_decorator(cache_page(60), name='get')
class TimeSeriesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = resolve_period(request)
        interval = (request.query_params.get("interval") or "day").lower()
        orders = role_scoped_orders(request.user, start, end)
        orders = apply_optional_filters(orders, request, request.user)

        trunc_map = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}
        trunc = trunc_map.get(interval, TruncDay)

        qs = (
            orders
            .annotate(d=trunc("created_at"))
            .values("d")
            .annotate(
                orders_count=Count("id"),
                sum_total=Sum("total_amount"),
                completed_count=Count("id", filter=Q(status=Order.STATUS_COMPLETED)),
                cancelled_count=Count("id", filter=Q(status__in=CANCEL_STATUSES)),
            )
            .order_by("d")
        )

        result = [
            {
                "date": r["d"].date().isoformat(),
                "orders": r["orders_count"],
                "revenue": int(r["sum_total"] or 0),
                "completed": r["completed_count"],
                "cancelled": r["cancelled_count"],
            }
            for r in qs
        ]
        return Response(result)


@method_decorator(cache_page(60), name='get')
class ByManagerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = resolve_period(request)
        orders = role_scoped_orders(request.user, start, end)
        orders = apply_optional_filters(orders, request, request.user)

        qs = (
            orders
            .values("responsible_id", "responsible__last_name", "responsible__first_name")
            .annotate(
                orders_count=Count("id"),
                sum_total=Sum("total_amount"),
                completed_count=Count("id", filter=Q(status=Order.STATUS_COMPLETED)),
                cancelled_count=Count("id", filter=Q(status__in=CANCEL_STATUSES)),
            )
            .order_by("-sum_total")
        )

        result = [
            {
                "manager_id": r["responsible_id"],
                "name": f"{(r.get('responsible__last_name') or '').strip()} {(r.get('responsible__first_name') or '').strip()}".strip(),
                "orders": r["orders_count"],
                "revenue": int(r["sum_total"] or 0),
                "completed": r["completed_count"],
                "cancelled": r["cancelled_count"],
            }
            for r in qs
        ]
        return Response(result)


@method_decorator(cache_page(60), name='get')
class TopProductsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = resolve_period(request)
        limit = int(request.query_params.get("limit") or 10)
        orders = role_scoped_orders(request.user, start, end)
        orders = apply_optional_filters(orders, request, request.user)
        items = OrderItem.objects.filter(order__in=orders)

        agg = (
            items
            .values("product_code", "product_name")
            .annotate(
                qty=Sum("quantity"),
                revenue=Sum(F("price") * F("quantity")),
            )
            .order_by("-revenue")[:limit]
        )

        return Response([
            {
                "product_code": a["product_code"],
                "product_name": a["product_name"],
                "quantity": int(a["qty"] or 0),
                "revenue": int(a["revenue"] or 0),
            }
            for a in agg
        ])


@method_decorator(cache_page(60), name='get')
class ExportOrdersCSVView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start, end = resolve_period(request)
        orders = (
            apply_optional_filters(
                role_scoped_orders(request.user, start, end), request, request.user
            )
            .select_related("responsible", "client")
            .only("order_number", "created_at", "status", "total_amount", "responsible__username", "client__id")
        )

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="orders_report.csv"'
        resp.write("order_number;created_at;status;responsible;client;total_amount\n")
        for o in orders.iterator():
            responsible = getattr(o.responsible, "username", "") or ""
            client = getattr(o.client, "id", "")
            line = f"{o.order_number};{o.created_at:%Y-%m-%d %H:%M};{o.status};{responsible};{client};{int(o.total_amount or 0)}\n"
            resp.write(line)
        return resp


