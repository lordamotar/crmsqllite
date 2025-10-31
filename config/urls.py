from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('clients/', include('apps.clients.urls')),
    path('orders/', include('apps.orders.urls')),
    path('products/', include('apps.products.urls')),
    path('cities/', include('apps.cities.urls')),
    path('profile/', include('apps.user_profile.urls')),
    path(
        '',
        RedirectView.as_view(
            pattern_name='dashboard:dashboard', permanent=False
        )
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
