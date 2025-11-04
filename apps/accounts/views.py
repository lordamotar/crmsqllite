from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect

from .models import User, Role, Position, Branch
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer
)


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Пользователь успешно зарегистрирован'
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    """Вход пользователя"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        login(request, user)
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Пользователь успешно вошел в систему'
        }, status=status.HTTP_200_OK)

class ProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и обновление профиля"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserProfileSerializer

class ChangePasswordView(generics.UpdateAPIView):
    """Смена пароля"""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'message': 'Пароль успешно изменен'
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Выход пользователя"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({
            'message': 'Выход из системы успешен'
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({
            'error': 'Недействительный токен'
        }, status=status.HTTP_400_BAD_REQUEST)


# Обычные Django views для веб-интерфейса
@csrf_protect
def login_view(request):
    """Страница входа в систему"""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Проверяем активность пользователя
                if not user.is_active:
                    messages.error(request, 'Учетная запись отключена. Обратитесь к администратору.')
                else:
                    login(request, user)
                    
                    # Настройка сессии для "запомнить меня"
                    # remember_me будет "1" если чекбокс отмечен, None если не отмечен
                    if remember_me:
                        # Сессия на 2 недели
                        request.session.set_expiry(1209600)
                        request.session.modified = True
                    else:
                        # Сессия истекает при закрытии браузера
                        request.session.set_expiry(0)
                        request.session.modified = True
                    
                    # Перенаправление на следующую страницу
                    next_page = request.GET.get('next', 'dashboard:dashboard')
                    return redirect(next_page)
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
        else:
            messages.error(request, 'Пожалуйста, заполните все поля')
    
    return render(request, 'accounts/login.html')


@login_required(login_url='accounts:login')
def logout_user_view(request):
    """Выход из системы"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('accounts:login')


@login_required
def users_list(request):
    """Список пользователей"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра списка пользователей')
        return redirect('dashboard:dashboard')
    
    # Получаем параметры пагинации
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    # Поиск
    search_query = request.GET.get('search', '').strip()
    users_qs = User.objects.select_related('role', 'position', 'branch', 'manager').all()
    
    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Сортировка
    sort_by = request.GET.get('sort', '-created_at')
    users_qs = users_qs.order_by(sort_by)
    
    # Пагинация
    paginator = Paginator(users_qs, per_page)
    page = request.GET.get('page', 1)
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    # Добавляем информацию о пагинации
    users.start_index = (users.number - 1) * per_page + 1
    users.end_index = min(users.start_index + per_page - 1, paginator.count)
    users.per_page = per_page
    
    return render(request, 'accounts/manage/users_list.html', {
        'users': users,
        'per_page': per_page,
    })


@login_required
def add_user(request):
    """Добавление нового пользователя"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для добавления пользователей')
        return redirect('dashboard:dashboard')
    
    # Получаем справочники для форм
    roles = Role.objects.all().order_by('name')
    positions = Position.objects.all().order_by('name')
    branches = Branch.objects.filter(is_active=True).order_by('name')
    managers = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            role_id = request.POST.get('role')
            position_id = request.POST.get('position') or None
            branch_id = request.POST.get('branch') or None
            manager_id = request.POST.get('manager') or None
            
            if not username or not password:
                messages.error(request, 'Логин и пароль обязательны')
            elif not role_id:
                messages.error(request, 'Роль обязательна')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Пользователь с таким логином уже существует')
            elif email and User.objects.filter(email=email).exists():
                messages.error(request, 'Пользователь с таким email уже существует')
            else:
                with transaction.atomic():
                    role = Role.objects.get(pk=role_id)
                    user = User.objects.create_user(
                        username=username,
                        email=email or f'{username}@example.com',
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        role=role,
                    )
                    
                    if position_id:
                        user.position_id = position_id
                    if branch_id:
                        user.branch_id = branch_id
                    if manager_id:
                        user.manager_id = manager_id
                    user.save()
                    
                    messages.success(request, f'Пользователь {user.username} успешно создан')
                    return redirect('accounts:users_list')
        except Role.DoesNotExist:
            messages.error(request, 'Выбранная роль не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка при создании пользователя: {str(e)}')
    
    return render(request, 'accounts/manage/add_user.html', {
        'roles': roles,
        'positions': positions,
        'branches': branches,
        'managers': managers,
    })


@login_required
def edit_user(request, user_id):
    """Редактирование пользователя"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования пользователей')
        return redirect('dashboard:dashboard')
    
    user = get_object_or_404(User, pk=user_id)
    can_set_password = request.user.is_superuser
    is_editing_self = request.user.id == user.id
    
    # Получаем справочники для форм
    roles = Role.objects.all().order_by('name')
    positions = Position.objects.all().order_by('name')
    branches = Branch.objects.filter(is_active=True).order_by('name')
    managers = User.objects.filter(is_active=True).exclude(pk=user.id).order_by('last_name', 'first_name')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password', '')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            role_id = request.POST.get('role')
            position_id = request.POST.get('position') or None
            branch_id = request.POST.get('branch') or None
            manager_id = request.POST.get('manager') or None
            is_active_post = request.POST.get('is_active')
            is_active = is_active_post == 'on'
            is_staff = request.POST.get('is_staff') == 'on' if request.user.is_superuser else user.is_staff
            is_superuser = request.POST.get('is_superuser') == 'on' if request.user.is_superuser else user.is_superuser
            
            # Логируем для отладки
            import logging
            logger = logging.getLogger('apps.accounts')
            logger.info(f'Edit user {user.id}: is_active from POST={is_active_post}, parsed={is_active}, current={user.is_active}, is_editing_self={is_editing_self}')
            
            # Защита: нельзя деактивировать самого себя
            if is_editing_self and not is_active:
                messages.error(request, 'Вы не можете деактивировать самого себя')
            elif username != user.username and User.objects.filter(username=username).exclude(pk=user.id).exists():
                messages.error(request, 'Пользователь с таким логином уже существует')
            elif email and email != user.email and User.objects.filter(email=email).exclude(pk=user.id).exists():
                messages.error(request, 'Пользователь с таким email уже существует')
            elif not role_id:
                messages.error(request, 'Роль обязательна')
            else:
                with transaction.atomic():
                    # Сохраняем старые значения для восстановления в случае ошибки
                    old_username = user.username
                    old_email = user.email
                    old_is_active = user.is_active
                    
                    user.username = username
                    if email:
                        user.email = email
                    user.first_name = first_name
                    user.last_name = last_name
                    
                    # Сохранение is_active: всегда для других, только активация для себя
                    if not is_editing_self:
                        # Редактирую другого пользователя - сохраняю любое значение
                        logger.info(f'BEFORE save: user.is_active={user.is_active}, setting to={is_active}')
                        user.is_active = is_active
                        logger.info(f'AFTER assignment: user.is_active={user.is_active}')
                    else:
                        # Редактирую самого себя - можно только активировать, деактивация запрещена
                        if is_active:
                            user.is_active = True
                            logger.info(f'Setting is_active for self: {old_is_active} -> True')
                        # Если is_active=False, то не меняем (оставляем текущее значение)
                        else:
                            logger.info(f'Keeping is_active for self: {old_is_active} (prevented deactivation)')
                    # Защита: нельзя убрать права staff/superuser у самого себя
                    if not is_editing_self:
                        if request.user.is_superuser:
                            user.is_staff = is_staff
                            user.is_superuser = is_superuser
                    user.role_id = role_id
                    user.position_id = position_id
                    user.branch_id = branch_id
                    user.manager_id = manager_id
                    
                    # Подготавливаем список полей для обновления
                    update_fields = [
                        'username', 'email', 'first_name', 'last_name', 
                        'is_active', 'is_staff', 'is_superuser',
                        'role_id', 'position_id', 'branch_id', 'manager_id'
                    ]
                    
                    if password and can_set_password:
                        user.set_password(password)
                        update_fields.append('password')  # Пароль уже захеширован set_password
                    
                    # Явно указываем поля для сохранения, чтобы гарантировать обновление
                    user.save(update_fields=update_fields)
                    
                    # Проверяем, что значение действительно сохранилось
                    user.refresh_from_db()
                    logger.info(f'User {user.id} saved and refreshed: is_active={user.is_active}, is_staff={user.is_staff}, is_superuser={user.is_superuser}')
                    
                    # Обновляем сессию если редактируем сами себя
                    if is_editing_self:
                        from django.contrib.auth import update_session_auth_hash
                        # Обновляем хеш сессии при смене пароля
                        if password:
                            update_session_auth_hash(request, user)
                        # Обновляем данные пользователя в сессии
                        request.user.refresh_from_db()
                    
                    messages.success(request, f'Пользователь {user.username} успешно обновлен')
                    return redirect('accounts:users_list')
        except Role.DoesNotExist:
            messages.error(request, 'Выбранная роль не найдена')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении пользователя: {str(e)}')
    
    return render(request, 'accounts/manage/edit_user.html', {
        'u': user,
        'can_set_password': can_set_password,
        'roles': roles,
        'positions': positions,
        'branches': branches,
        'managers': managers,
    })


# Роли
@login_required
def roles_list(request):
    """Список ролей"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра ролей')
        return redirect('dashboard:dashboard')
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    search_query = request.GET.get('search', '').strip()
    roles_qs = Role.objects.all()
    
    if search_query:
        roles_qs = roles_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    sort_by = request.GET.get('sort', 'name')
    roles_qs = roles_qs.order_by(sort_by)
    
    paginator = Paginator(roles_qs, per_page)
    page = request.GET.get('page', 1)
    try:
        roles = paginator.page(page)
    except PageNotAnInteger:
        roles = paginator.page(1)
    except EmptyPage:
        roles = paginator.page(paginator.num_pages)
    
    roles.start_index = (roles.number - 1) * per_page + 1
    roles.end_index = min(roles.start_index + per_page - 1, paginator.count)
    roles.per_page = per_page
    
    return render(request, 'accounts/manage/roles_list.html', {
        'roles': roles,
        'per_page': per_page,
    })


@login_required
def add_role(request):
    """Добавление новой роли"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для добавления ролей')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'Название роли обязательно')
            elif Role.objects.filter(name=name).exists():
                messages.error(request, 'Роль с таким названием уже существует')
            else:
                with transaction.atomic():
                    role = Role.objects.create(
                        name=name,
                        description=description or None,
                    )
                    messages.success(request, f'Роль {role.name} успешно создана')
                    return redirect('accounts:roles_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании роли: {str(e)}')
    
    return render(request, 'accounts/manage/role_form.html')


@login_required
def edit_role(request, role_id):
    """Редактирование роли"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования ролей')
        return redirect('dashboard:dashboard')
    
    role = get_object_or_404(Role, pk=role_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'Название роли обязательно')
            elif name != role.name and Role.objects.filter(name=name).exists():
                messages.error(request, 'Роль с таким названием уже существует')
            else:
                with transaction.atomic():
                    role.name = name
                    role.description = description or None
                    role.save()
                    messages.success(request, f'Роль {role.name} успешно обновлена')
                    return redirect('accounts:roles_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении роли: {str(e)}')
    
    return render(request, 'accounts/manage/role_form.html', {
        'role': role,
    })


# Должности
@login_required
def positions_list(request):
    """Список должностей"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра должностей')
        return redirect('dashboard:dashboard')
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    search_query = request.GET.get('search', '').strip()
    positions_qs = Position.objects.all()
    
    if search_query:
        positions_qs = positions_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    sort_by = request.GET.get('sort', 'name')
    positions_qs = positions_qs.order_by(sort_by)
    
    paginator = Paginator(positions_qs, per_page)
    page = request.GET.get('page', 1)
    try:
        positions = paginator.page(page)
    except PageNotAnInteger:
        positions = paginator.page(1)
    except EmptyPage:
        positions = paginator.page(paginator.num_pages)
    
    positions.start_index = (positions.number - 1) * per_page + 1
    positions.end_index = min(positions.start_index + per_page - 1, paginator.count)
    positions.per_page = per_page
    
    return render(request, 'accounts/manage/positions_list.html', {
        'positions': positions,
        'per_page': per_page,
    })


@login_required
def add_position(request):
    """Добавление новой должности"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для добавления должностей')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'Название должности обязательно')
            elif Position.objects.filter(name=name).exists():
                messages.error(request, 'Должность с таким названием уже существует')
            else:
                with transaction.atomic():
                    position = Position.objects.create(
                        name=name,
                        description=description or None,
                    )
                    messages.success(request, f'Должность {position.name} успешно создана')
                    return redirect('accounts:positions_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании должности: {str(e)}')
    
    return render(request, 'accounts/manage/position_form.html')


@login_required
def edit_position(request, position_id):
    """Редактирование должности"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования должностей')
        return redirect('dashboard:dashboard')
    
    position = get_object_or_404(Position, pk=position_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            
            if not name:
                messages.error(request, 'Название должности обязательно')
            elif name != position.name and Position.objects.filter(name=name).exists():
                messages.error(request, 'Должность с таким названием уже существует')
            else:
                with transaction.atomic():
                    position.name = name
                    position.description = description or None
                    position.save()
                    messages.success(request, f'Должность {position.name} успешно обновлена')
                    return redirect('accounts:positions_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении должности: {str(e)}')
    
    return render(request, 'accounts/manage/position_form.html', {
        'position': position,
    })


# Филиалы
@login_required
def branches_list(request):
    """Список филиалов"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра филиалов')
        return redirect('dashboard:dashboard')
    
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    search_query = request.GET.get('search', '').strip()
    branches_qs = Branch.objects.all()
    
    if search_query:
        branches_qs = branches_qs.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    sort_by = request.GET.get('sort', 'name')
    branches_qs = branches_qs.order_by(sort_by)
    
    paginator = Paginator(branches_qs, per_page)
    page = request.GET.get('page', 1)
    try:
        branches = paginator.page(page)
    except PageNotAnInteger:
        branches = paginator.page(1)
    except EmptyPage:
        branches = paginator.page(paginator.num_pages)
    
    branches.start_index = (branches.number - 1) * per_page + 1
    branches.end_index = min(branches.start_index + per_page - 1, paginator.count)
    branches.per_page = per_page
    
    return render(request, 'accounts/manage/branches_list.html', {
        'branches': branches,
        'per_page': per_page,
    })


@login_required
def add_branch(request):
    """Добавление нового филиала"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для добавления филиалов')
        return redirect('dashboard:dashboard')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            city = request.POST.get('city', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip() or None
            email = request.POST.get('email', '').strip() or None
            is_active = request.POST.get('is_active') == 'on'
            
            if not name or not city:
                messages.error(request, 'Название и город обязательны')
            else:
                with transaction.atomic():
                    branch = Branch.objects.create(
                        name=name,
                        city=city,
                        address=address or '',
                        phone=phone,
                        email=email,
                        is_active=is_active,
                    )
                    messages.success(request, f'Филиал {branch.name} успешно создан')
                    return redirect('accounts:branches_list')
        except Exception as e:
            messages.error(request, f'Ошибка при создании филиала: {str(e)}')
    
    return render(request, 'accounts/manage/branch_form.html')


@login_required
def edit_branch(request, branch_id):
    """Редактирование филиала"""
    from django.db import transaction
    
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования филиалов')
        return redirect('dashboard:dashboard')
    
    branch = get_object_or_404(Branch, pk=branch_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            city = request.POST.get('city', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip() or None
            email = request.POST.get('email', '').strip() or None
            is_active = request.POST.get('is_active') == 'on'
            
            if not name or not city:
                messages.error(request, 'Название и город обязательны')
            else:
                with transaction.atomic():
                    branch.name = name
                    branch.city = city
                    branch.address = address or ''
                    branch.phone = phone
                    branch.email = email
                    branch.is_active = is_active
                    branch.save()
                    messages.success(request, f'Филиал {branch.name} успешно обновлен')
                    return redirect('accounts:branches_list')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении филиала: {str(e)}')
    
    return render(request, 'accounts/manage/branch_form.html', {
        'branch': branch,
    })