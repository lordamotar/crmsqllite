from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views import View
from django.contrib.auth import get_user_model

from apps.orders.models import Order


def _context_common(request):
    # Источники: из констант модели
    sources = [s[0] for s in Order.SOURCE_CHOICES]

    # Менеджеры: зона видимости пользователя
    User = get_user_model()
    if request.user.is_superuser:
        managers = list(User.objects.filter(is_active=True).order_by('last_name', 'first_name').values('id', 'first_name', 'last_name', 'username'))
    elif hasattr(request.user, 'get_subordinates'):
        subs = request.user.get_subordinates().values('id', 'first_name', 'last_name', 'username')
        managers = [{
            'id': request.user.id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'username': request.user.username,
        }] + list(subs)
    else:
        managers = [{
            'id': request.user.id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'username': request.user.username,
        }]

    return {
        'sources': sources,
        'managers': managers,
    }


@method_decorator(login_required, name="dispatch")
class AnalyticsOverviewPage(View):
    def get(self, request):
        return render(request, "analytics/overview.html", _context_common(request))


@method_decorator(login_required, name="dispatch")
class AnalyticsByManagerPage(View):
    def get(self, request):
        return render(request, "analytics/by_manager.html", _context_common(request))


@method_decorator(login_required, name="dispatch")
class AnalyticsTopProductsPage(View):
    def get(self, request):
        return render(request, "analytics/top_products.html", _context_common(request))


