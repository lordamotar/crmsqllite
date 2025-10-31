from django.urls import path
from . import views

app_name = 'cities'

urlpatterns = [
    path('', views.cities_list, name='cities_list'),
    path('add/', views.add_city, name='add_city'),
    path('edit/<int:city_id>/', views.edit_city, name='edit_city'),
    path('delete/<int:city_id>/', views.delete_city, name='delete_city'),
]
