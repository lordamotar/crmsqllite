from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand
from django.core.exceptions import ValidationError
from apps.accounts.models import User, Role


class Command(BaseCommand):
    """Кастомная команда создания суперпользователя с автоматическим назначением роли"""
    
    def handle(self, *args, **options):
        # Получаем или создаем роль admin
        admin_role, created = Role.objects.get_or_create(
            name='admin',
            defaults={'description': 'Администратор системы'}
        )
        
        # Добавляем роль в опции
        options['role'] = admin_role
        
        try:
            super().handle(*args, **options)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка создания суперпользователя: {e}')
            )
            return
        
        # Находим созданного пользователя и назначаем роль
        email = options.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                user.role = admin_role
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Роль "{admin_role.name}" назначена пользователю {email}')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Пользователь с email {email} не найден')
                )
