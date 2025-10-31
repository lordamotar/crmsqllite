from urllib.parse import quote

from django.conf import settings
from django.shortcuts import resolve_url, redirect


class LoginRequiredMiddleware:
    """Глобально перенаправляет неавторизованных на страницу логина.

    Исключая явные публичные пути: статика/медиа, логин/логаут, админ-логин,
    и все API под /api/accounts/ (логин/refresh и т.п.).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_prefixes = (
            '/static/', '/media/',
            '/accounts/login/', '/accounts/logout/',
            '/admin/login/', '/admin/js/',
            '/api/accounts/',
            '/favicon.ico',
        )

    def __call__(self, request):
        path = request.path

        if request.user.is_authenticated:
            return self.get_response(request)

        # Разрешаем публичные пути
        for prefix in self.exempt_prefixes:
            if path.startswith(prefix):
                return self.get_response(request)

        login_url = resolve_url(getattr(settings, 'LOGIN_URL', 'accounts:login'))
        # Добавляем next для возврата после логина
        return redirect(f"{login_url}?next={quote(path)}")


