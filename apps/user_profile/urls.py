from django.urls import path
from . import views

app_name = 'user_profile'

urlpatterns = [
    path('', views.profile_settings, name='profile_settings'),
    path('update/', views.update_profile_ajax, name='update_profile_ajax'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('reset-avatar/', views.reset_avatar, name='reset_avatar'),
    path('change-password/', views.change_password, name='change_password'),
]
