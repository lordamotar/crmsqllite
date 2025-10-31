from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.orders_list, name='orders_list'),
    path('add/', views.add_order, name='add_order'),
    path('<int:pk>/edit/', views.edit_order, name='edit_order'),
    path('client-lookup/', views.client_lookup, name='client_lookup'),
    path('product-search/', views.product_search, name='product_search'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
]
