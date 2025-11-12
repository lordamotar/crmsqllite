from rest_framework import permissions


class IsDepartmentManagerOrAdmin(permissions.BasePermission):
    """Проверка прав начальника отдела или админа для просмотра отчетов."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        role_name = getattr(request.user.role, 'name', '').lower()
        return role_name in ('admin', 'начальник отдела', 'department_manager', 'manager')


class CanViewTimeclockReports(permissions.BasePermission):
    """Права на просмотр отчетов табеля."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role_name = getattr(request.user.role, 'name', '').lower()
        return role_name in ('admin', 'начальник отдела', 'department_manager', 'старший менеджер', 'senior_manager', 'manager')

