from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlanViewSet, PlanAssignmentViewSet, plans_list, add_plan, edit_plan

app_name = 'plans'

router = DefaultRouter()
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'plan-assignments', PlanAssignmentViewSet, basename='plan-assignment')

urlpatterns = [
    path('', plans_list, name='plans_list'),
    path('add/', add_plan, name='add_plan'),
    path('<int:pk>/edit/', edit_plan, name='edit_plan'),
    path('api/', include(router.urls)),
]

