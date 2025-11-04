from django.urls import path
from .views_pages import (
    AnalyticsOverviewPage,
    AnalyticsByManagerPage,
    AnalyticsTopProductsPage,
)

app_name = "analytics"

urlpatterns = [
    path("", AnalyticsOverviewPage.as_view(), name="overview_page"),
    path("by-manager/", AnalyticsByManagerPage.as_view(), name="by_manager_page"),
    path("top-products/", AnalyticsTopProductsPage.as_view(), name="top_products_page"),
]


