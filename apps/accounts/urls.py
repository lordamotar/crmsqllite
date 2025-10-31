from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # API endpoints
    path('api/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/login/', views.LoginView.as_view(), name='api_login'),
    path('api/logout/', views.logout_view, name='api_logout'),
    path('api/profile/', views.ProfileView.as_view(), name='api_profile'),
    path('api/change-password/', views.ChangePasswordView.as_view(), name='api_change_password'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    
    # Web interface endpoints
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_user_view, name='logout'),
]