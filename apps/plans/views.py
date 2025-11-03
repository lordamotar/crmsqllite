from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json

from .models import Plan, PlanAssignment
from .serializers import PlanSerializer, PlanListSerializer, PlanAssignmentSerializer
from .services import recalc_assignment_progress, recalc_plan_progress


class PlanViewSet(viewsets.ModelViewSet):
    """ViewSet для управления планами"""
    
    queryset = Plan.objects.select_related('created_by').prefetch_related('assignments').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['created_by', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-start_date', '-created_at']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return PlanListSerializer
        return PlanSerializer
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от роли пользователя"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Админы видят все планы
        if user.is_superuser:
            return queryset
        
        # Начальники видят свои планы и планы своих подчиненных
        # Менеджеры видят только планы, где они назначены
        subordinates_ids = list(user.get_subordinates().values_list('id', flat=True))
        
        # Планы, созданные пользователем или где он назначен
        return queryset.filter(
            Q(created_by=user) |
            Q(assignments__manager__in=subordinates_ids) |
            Q(assignments__manager=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """Создание плана с установкой создателя"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def recalc(self, request, pk=None):
        """Пересчитать прогресс всех назначений плана"""
        plan = self.get_object()
        updated = recalc_plan_progress(plan)
        
        return Response({
            'updated': [
                {
                    'id': a.id,
                    'manager': a.manager.id,
                    'manager_name': a.manager.short_name,
                    'achieved_count': a.achieved_count,
                    'achieved_sum': float(a.achieved_sum),
                    'is_achieved': a.is_achieved
                }
                for a in updated
            ]
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def my_plans(self, request):
        """Получить планы, где текущий пользователь назначен"""
        plans = self.get_queryset().filter(assignments__manager=request.user).distinct()
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active_plans(self, request):
        """Получить активные планы (текущая дата в периоде)"""
        today = timezone.now().date()
        plans = self.get_queryset().filter(
            start_date__lte=today,
            end_date__gte=today
        )
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


class PlanAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet для управления назначениями планов"""
    
    queryset = PlanAssignment.objects.select_related('plan', 'manager').all()
    serializer_class = PlanAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['plan', 'manager', 'is_achieved']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Фильтрация queryset в зависимости от роли пользователя"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        # Менеджеры видят только свои назначения
        # Начальники видят назначения своих подчиненных
        subordinates_ids = list(user.get_subordinates().values_list('id', flat=True))
        subordinates_ids.append(user.id)
        
        return queryset.filter(
            Q(manager__in=subordinates_ids) |
            Q(plan__created_by=user)
        ).distinct()
    
    @action(detail=True, methods=['post'])
    def recalc(self, request, pk=None):
        """Пересчитать прогресс конкретного назначения"""
        assignment = self.get_object()
        recalc_assignment_progress(assignment)
        return Response(PlanAssignmentSerializer(assignment).data)


@login_required
def plans_list(request):
    """Список планов для шаблона"""
    
    # Получаем параметры пагинации
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10
    
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'start_date')
    order = request.GET.get('order', 'desc')
    
    # Маппинг полей для сортировки
    sort_mapping = {
        'name': 'name',
        'start_date': 'start_date',
        'end_date': 'end_date',
        'created_by': 'created_by__last_name',
        'created_at': 'created_at',
    }
    
    # Определяем поле для сортировки
    sort_field = sort_mapping.get(sort_by, 'start_date')
    
    # Определяем направление сортировки
    if order == 'asc':
        sort_field = sort_field
    else:
        if not sort_field.startswith('-'):
            sort_field = f'-{sort_field}'
    
    # Получаем планы
    plans_qs = Plan.objects.select_related('created_by').prefetch_related(
        'assignments__manager'
    ).all()
    
    # Фильтрация по роли пользователя
    user = request.user
    if not user.is_superuser:
        subordinates_ids = list(user.get_subordinates().values_list('id', flat=True))
        plans_qs = plans_qs.filter(
            Q(created_by=user) |
            Q(assignments__manager__in=subordinates_ids) |
            Q(assignments__manager=user)
        ).distinct()
    
    # Применяем фильтры
    if request.GET.get('search'):
        search_term = request.GET.get('search')
        plans_qs = plans_qs.filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(created_by__first_name__icontains=search_term) |
            Q(created_by__last_name__icontains=search_term)
        )
    
    if request.GET.get('active'):
        today = timezone.now().date()
        plans_qs = plans_qs.filter(
            start_date__lte=today,
            end_date__gte=today
        )
    
    # Сортировка
    plans_qs = plans_qs.order_by(sort_field)
    
    # Пагинация
    paginator = Paginator(plans_qs, per_page)
    page = request.GET.get('page', 1)
    try:
        plans = paginator.page(page)
    except PageNotAnInteger:
        plans = paginator.page(1)
    except EmptyPage:
        plans = paginator.page(paginator.num_pages)
    
    # Добавляем информацию о пагинации
    plans.start_index = plans.start_index() if hasattr(plans, 'start_index') else (plans.number - 1) * per_page + 1
    plans.end_index = min(plans.start_index + per_page - 1, paginator.count)
    
    # Добавляем дополнительную информацию к каждому плану для шаблона
    for plan in plans:
        plan.assignments_count = plan.assignments.count()
        plan.managers_list = list(plan.assignments.select_related('manager').all()[:3])
        plan.extra_managers_count = max(0, plan.assignments_count - 3)
    
    context = {
        'plans': plans,
        'per_page': per_page,
        'sort_by': sort_by,
        'order': order,
        'user': request.user,
    }
    
    return render(request, 'plans/plans_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def add_plan(request):
    """Страница создания плана и обработчик POST"""
    from apps.accounts.models import User
    
    if request.method == 'GET':
        # Получаем список подчиненных для выбора менеджеров
        subordinates = request.user.get_subordinates().filter(active=True).order_by('first_name', 'last_name')
        
        return render(
            request,
            'plans/plan_form.html',
            {
                'is_edit': False,
                'subordinates': subordinates,
            }
        )
    
    # POST JSON
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')
        
        name = payload.get('name')
        start_date = payload.get('start_date')
        end_date = payload.get('end_date')
        description = payload.get('description', '')
        assignments = payload.get('assignments', [])
        
        if not name or not start_date or not end_date:
            return JsonResponse(
                {'status': 'error', 'message': 'Название, дата начала и дата окончания обязательны'},
                status=400,
            )
        
        try:
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start > end:
                return JsonResponse(
                    {'status': 'error', 'message': 'Дата начала не может быть позже даты окончания'},
                    status=400,
                )
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'message': 'Неверный формат даты'},
                status=400,
            )
        
        with transaction.atomic():
            plan = Plan(
                name=name,
                description=description,
                start_date=start,
                end_date=end,
                created_by=request.user,
            )
            plan.save()
            
            # Создаем назначения
            for assignment_data in assignments:
                manager_id = assignment_data.get('manager_id')
                target_count = int(assignment_data.get('target_count', 0))
                target_sum = float(assignment_data.get('target_sum', 0))
                criteria_operator = assignment_data.get('criteria_operator', 'both')
                
                if not manager_id:
                    continue
                
                try:
                    manager = User.objects.get(pk=manager_id)
                except User.DoesNotExist:
                    continue
                
                # Проверяем, что менеджер является подчиненным
                if not request.user.is_manager_of(manager):
                    continue
                
                PlanAssignment.objects.create(
                    plan=plan,
                    manager=manager,
                    target_count=target_count,
                    target_sum=target_sum,
                    criteria_operator=criteria_operator,
                )
            
            # Пересчитываем прогресс для всех назначений
            from .services import recalc_plan_progress
            recalc_plan_progress(plan)
        
        return JsonResponse({
            'status': 'success',
            'message': 'План успешно создан',
            'plan_id': plan.id,
            'redirect_url': f'/plans/',
        })
    
    return HttpResponseBadRequest('Unsupported Content-Type')


@login_required
@require_http_methods(["GET", "POST"])
def edit_plan(request, pk):
    """Страница редактирования плана и обработчик POST"""
    from apps.accounts.models import User
    
    plan = get_object_or_404(
        Plan.objects.prefetch_related('assignments__manager'),
        pk=pk
    )
    
    # Проверка прав доступа
    if not request.user.is_superuser and plan.created_by != request.user:
        return JsonResponse(
            {'status': 'error', 'message': 'У вас нет прав для редактирования этого плана'},
            status=403,
        )
    
    if request.method == 'GET':
        # Получаем список подчиненных
        subordinates = request.user.get_subordinates().filter(active=True).order_by('first_name', 'last_name')
        
        # Предзаполняем данные назначений
        assignments_data = []
        for assignment in plan.assignments.all():
            assignments_data.append({
                'id': assignment.id,
                'manager_id': assignment.manager.id,
                'manager_name': assignment.manager.short_name,
                'target_count': assignment.target_count,
                'target_sum': float(assignment.target_sum),
                'criteria_operator': assignment.criteria_operator,
                'achieved_count': assignment.achieved_count,
                'achieved_sum': float(assignment.achieved_sum),
                'is_achieved': assignment.is_achieved,
            })
        
        return render(
            request,
            'plans/plan_form.html',
            {
                'is_edit': True,
                'plan': plan,
                'subordinates': subordinates,
                'assignments_data_json': json.dumps(assignments_data),
            }
        )
    
    # POST JSON
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')
        
        name = payload.get('name')
        start_date = payload.get('start_date')
        end_date = payload.get('end_date')
        description = payload.get('description', '')
        assignments = payload.get('assignments', [])
        
        if not name or not start_date or not end_date:
            return JsonResponse(
                {'status': 'error', 'message': 'Название, дата начала и дата окончания обязательны'},
                status=400,
            )
        
        try:
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start > end:
                return JsonResponse(
                    {'status': 'error', 'message': 'Дата начала не может быть позже даты окончания'},
                    status=400,
                )
        except ValueError:
            return JsonResponse(
                {'status': 'error', 'message': 'Неверный формат даты'},
                status=400,
            )
        
        with transaction.atomic():
            plan.name = name
            plan.description = description
            plan.start_date = start
            plan.end_date = end
            plan.save()
            
            # Удаляем все старые назначения и создаем новые
            plan.assignments.all().delete()
            
            # Создаем новые назначения
            for assignment_data in assignments:
                manager_id = assignment_data.get('manager_id')
                target_count = int(assignment_data.get('target_count', 0))
                target_sum = float(assignment_data.get('target_sum', 0))
                criteria_operator = assignment_data.get('criteria_operator', 'both')
                
                if not manager_id:
                    continue
                
                try:
                    manager = User.objects.get(pk=manager_id)
                except User.DoesNotExist:
                    continue
                
                # Проверяем, что менеджер является подчиненным
                if not request.user.is_manager_of(manager):
                    continue
                
                PlanAssignment.objects.create(
                    plan=plan,
                    manager=manager,
                    target_count=target_count,
                    target_sum=target_sum,
                    criteria_operator=criteria_operator,
                )
            
            # Пересчитываем прогресс для всех назначений
            from .services import recalc_plan_progress
            recalc_plan_progress(plan)
        
        return JsonResponse({
            'status': 'success',
            'message': 'План успешно обновлен',
            'plan_id': plan.id,
            'redirect_url': f'/plans/',
        })
    
    return HttpResponseBadRequest('Unsupported Content-Type')

