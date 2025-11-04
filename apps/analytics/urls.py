from django.urls import path
from .views import (
    OverviewAPIView,
    TimeSeriesAPIView,
    ByManagerAPIView,
    TopProductsAPIView,
    ExportOrdersCSVView,
)

app_name = "analytics_api"

urlpatterns = [
    path("overview/", OverviewAPIView.as_view(), name="overview"),
    path("timeseries/", TimeSeriesAPIView.as_view(), name="timeseries"),
    path("by-manager/", ByManagerAPIView.as_view(), name="by_manager"),
    path("top-products/", TopProductsAPIView.as_view(), name="top_products"),
    path("export.csv", ExportOrdersCSVView.as_view(), name="export_csv"),
]


