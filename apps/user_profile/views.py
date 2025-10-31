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
import json

User = get_user_model()


@login_required(login_url='login')
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

    return render(request, 'user_profile/profile_settings.html', {
        'form': form,
        'profile': profile
    })


@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
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


@login_required(login_url='login')
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
