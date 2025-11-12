from django.utils import timezone
from django.shortcuts import redirect
from django.http import JsonResponse
import logging
from .models import WorkSession

logger = logging.getLogger(__name__)


class WorkSessionRequiredMiddleware:
    """Блокирует доступ к системе без активной рабочей сессии.
    
    Пользователь должен нажать "Начать работу" перед использованием системы.
    Исключения: страница timeclock, API endpoints для управления сессиями, статика, логин/логаут, админка.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Пути, которые доступны без активной сессии
        self.exempt_paths = (
            '/timeclock/',  # Страница для начала работы и все её подпути
            '/api/timeclock/',  # Все API endpoints timeclock (start, stop, status, heartbeat и т.д.)
            '/dashboard/',  # Dashboard - там есть кнопка "Начать работу"
            '/static/',
            '/media/',
            '/accounts/login/',
            '/accounts/logout/',
            '/admin/',
            '/favicon.ico',
            '/health',
        )

    def __call__(self, request):
        user = getattr(request, 'user', None)
        
        # Проверяем только для аутентифицированных пользователей
        if user and user.is_authenticated:
            path = request.path
            
            # Проверяем, является ли путь исключением
            is_exempt = any(path.startswith(exempt) for exempt in self.exempt_paths)
            
            if not is_exempt:
                # Проверяем наличие активной сессии
                try:
                    has_active_session = WorkSession.objects.filter(
                        user=user,
                        is_closed=False
                    ).exists()
                    
                    logger.info(
                        f'WorkSession check: user={user.username}, path={path}, method={request.method}, '
                        f'has_active_session={has_active_session}, is_exempt={is_exempt}'
                    )
                    
                    if not has_active_session:
                        logger.warning(
                            f'BLOCKING REQUEST: user={user.username}, path={path}, method={request.method} - '
                            f'no active work session'
                        )
                        # Для GET запросов - перенаправляем на страницу dashboard
                        if request.method == 'GET':
                            logger.warning(f'Redirecting GET request to dashboard: {path}')
                            return redirect('dashboard:dashboard')
                        # Для POST/PUT/DELETE запросов - возвращаем ошибку
                        else:
                            # Если это AJAX запрос - возвращаем JSON
                            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                               'application/json' in request.headers.get('Content-Type', ''):
                                logger.warning(f'Returning 403 JSON response for {path}')
                                return JsonResponse({
                                    'status': 'error',
                                    'message': 'Для работы в системе необходимо начать рабочую сессию. Перейдите на страницу "Табель" и нажмите "Начать работу".'
                                }, status=403)
                            # Иначе перенаправляем на dashboard
                            logger.warning(f'Redirecting POST request to dashboard: {path}')
                            return redirect('dashboard:dashboard')
                    else:
                        logger.debug(f'ALLOWING REQUEST: user={user.username}, path={path}, method={request.method} - active session exists')
                except Exception as e:
                    # В случае ошибки БД не блокируем доступ, но логируем
                    logger.error(f'Error checking work session for {path}: {e}', exc_info=True)
                    pass
        
        return self.get_response(request)


class TimeclockActivityMiddleware:
    """Обновляет last_activity для открытой сессии при каждом запросе пользователя."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                path = request.path
                if path.startswith('/static') or path.startswith('/health'):
                    return response
                session = (
                    WorkSession.objects.filter(user=user, is_closed=False)
                    .order_by('-start_time')
                    .first()
                )
                if session:
                    now = timezone.now()
                    if not session.last_activity or (now - session.last_activity).total_seconds() > 60:
                        session.last_activity = now
                        session.save(update_fields=['last_activity'])
        except Exception:
            # намеренно не мешаем основному запросу
            pass
        return response

