from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.clients_list, name='clients_list'),
    path('add/', views.add_client, name='add_client'),
    path('edit/<uuid:client_id>/', views.edit_client, name='edit_client'),
    path('delete/<uuid:client_id>/', views.delete_client, name='delete_client'),
    path('import-excel/', views.import_clients_excel, name='import_clients_excel'),
]
