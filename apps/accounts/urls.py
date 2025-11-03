from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

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
    
    # User management
    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    
    # Roles
    path('roles/', views.roles_list, name='roles_list'),
    path('roles/add/', views.add_role, name='add_role'),
    path('roles/<int:role_id>/edit/', views.edit_role, name='edit_role'),
    
    # Positions
    path('positions/', views.positions_list, name='positions_list'),
    path('positions/add/', views.add_position, name='add_position'),
    path('positions/<int:position_id>/edit/', views.edit_position, name='edit_position'),
    
    # Branches
    path('branches/', views.branches_list, name='branches_list'),
    path('branches/add/', views.add_branch, name='add_branch'),
    path('branches/<int:branch_id>/edit/', views.edit_branch, name='edit_branch'),
]