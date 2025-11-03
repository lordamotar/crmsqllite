from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from .models import UserProfile
from .forms import UserProfileForm
from apps.plans.models import PlanAssignment
import json
from decimal import Decimal

User = get_user_model()


@login_required(login_url='accounts:login')
def profile_settings(request):
    """Настройки профиля пользователя"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            # Сохраняем профиль
            profile = form.save()
            
            # Обновляем данные пользователя из таблицы users
            user = request.user
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name = form.cleaned_data.get('last_name', '')
            user.middle_name = form.cleaned_data.get('middle_name', '')
            user.email = form.cleaned_data.get('email', '')
            user.phone = form.cleaned_data.get('phone', '')
            user.bio = form.cleaned_data.get('bio', '')
            user.save()
            
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('user_profile:profile_settings')
    else:
        form = UserProfileForm(instance=profile, user=request.user)

    # Получаем планы менеджера, сгруппированные по месяцам
    assignments = PlanAssignment.objects.filter(
        manager=request.user
    ).select_related('plan').order_by('-plan__start_date', '-plan__created_at')
    
    # Группируем по месяцам (используем start_date плана)
    # Месяцы на русском
    month_names_ru = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    plans_by_month = {}
    for assignment in assignments:
        plan = assignment.plan
        month_key = plan.start_date.strftime('%Y-%m')
        month_name_ru = month_names_ru.get(plan.start_date.month, plan.start_date.strftime('%B'))
        month_display = f"{month_name_ru} {plan.start_date.year}"
        
        # Рассчитываем проценты выполнения
        count_percent = (Decimal(assignment.achieved_count) / Decimal(assignment.target_count) * 100) if assignment.target_count > 0 else Decimal(0)
        sum_percent = (assignment.achieved_sum / assignment.target_sum * 100) if assignment.target_sum > 0 else Decimal(0)
        
        if month_key not in plans_by_month:
            plans_by_month[month_key] = {
                'month_name': month_display,
                'month_key': month_key,
                'plans': []
            }
        
        plans_by_month[month_key]['plans'].append({
            'assignment': assignment,
            'plan': plan,
            'count_percent': count_percent,
            'sum_percent': sum_percent,
        })
    
    # Сортируем месяцы по убыванию
    sorted_months = sorted(plans_by_month.items(), key=lambda x: x[0], reverse=True)

    return render(request, 'user_profile/profile_settings.html', {
        'form': form,
        'profile': profile,
        'plans_by_month': dict(sorted_months),
    })


@login_required(login_url='accounts:login')
@csrf_exempt
@require_http_methods(["POST"])
def update_profile_ajax(request):
    """AJAX обновление профиля"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    try:
        data = json.loads(request.body)
        print(f"DEBUG: Получены данные: {data}")  # Отладочный вывод
        
        form = UserProfileForm(data, instance=profile, user=request.user)
        
        if form.is_valid():
            print(f"DEBUG: Форма валидна, сохраняем данные")  # Отладочный вывод
            # Сохраняем профиль и данные пользователя
            profile = form.save()
            
            print(f"DEBUG: Данные сохранены успешно")  # Отладочный вывод
            return JsonResponse({
                'success': True,
                'message': 'Профиль успешно обновлен!'
            })
        else:
            print(f"DEBUG: Ошибки формы: {form.errors}")  # Отладочный вывод
            return JsonResponse({
                'success': False,
                'message': 'Ошибка валидации формы',
                'errors': form.errors
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })


@login_required(login_url='accounts:login')
@csrf_exempt
@require_http_methods(["POST"])
def upload_avatar(request):
    """Загрузка аватара"""
    if 'avatar' in request.FILES:
        # Удаляем старый аватар если есть
        if request.user.avatar:
            request.user.avatar.delete()
        
        # Сохраняем новый аватар
        request.user.avatar = request.FILES['avatar']
        request.user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Аватар успешно загружен!',
            'avatar_url': request.user.avatar.url if request.user.avatar else None
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Файл не выбран'
        })


@login_required(login_url='accounts:login')
@csrf_exempt
@require_http_methods(["POST"])
def reset_avatar(request):
    """Сброс аватара"""
    if request.user.avatar:
        request.user.avatar.delete()
        request.user.avatar = None
        request.user.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Аватар сброшен!'
    })


@login_required(login_url='accounts:login')
@csrf_exempt
@require_http_methods(["POST"])
def change_password(request):
    """Изменение пароля пользователя"""
    try:
        data = json.loads(request.body)
        old_password = data.get('old_password', '')
        new_password1 = data.get('new_password1', '')
        new_password2 = data.get('new_password2', '')
        
        # Валидация
        if not old_password or not new_password1 or not new_password2:
            return JsonResponse({
                'success': False,
                'message': 'Все поля обязательны для заполнения'
            })
        
        if new_password1 != new_password2:
            return JsonResponse({
                'success': False,
                'message': 'Новые пароли не совпадают'
            })
        
        if len(new_password1) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Новый пароль должен содержать минимум 8 символов'
            })
        
        # Проверка старого пароля
        user = request.user
        if not check_password(old_password, user.password):
            return JsonResponse({
                'success': False,
                'message': 'Неверный текущий пароль'
            })
        
        # Установка нового пароля
        user.set_password(new_password1)
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Пароль успешно изменен!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })
