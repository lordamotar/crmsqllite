from django.core.management.base import BaseCommand
from apps.accounts.models import User, Role


class Command(BaseCommand):
    """Создаёт базовые роли и тестовых пользователей (идемпотентно)."""

    help = "Create base roles and demo users with predefined passwords"

    def handle(self, *args, **options):
        roles = {
            'admin': 'Администратор системы',
            'manager': 'Менеджер',
            'accountant': 'Бухгалтер',
            'operator': 'Оператор',
        }

        for name, description in roles.items():
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создана роль: {name}'))

        users = [
            ('admin@example.com', 'admin', 'admin123', 'admin'),
            ('manager1@example.com', 'manager1', 'manager123', 'manager'),
            ('accountant1@example.com', 'accountant1', 'accountant123', 'accountant'),
            ('operator1@example.com', 'operator1', 'operator123', 'operator'),
        ]

        for email, username, password, role_name in users:
            role = Role.objects.get(name=role_name)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'role': role,
                    'is_staff': role_name in ['admin', 'manager'],
                    'is_superuser': role_name == 'admin',
                },
            )

            # Обновляем учётные данные и роль на всякий случай
            user.username = username
            user.role = role
            user.is_staff = role_name in ['admin', 'manager']
            user.is_superuser = role_name == 'admin'
            user.set_password(password)
            user.save()

            action = 'Создан' if created else 'Обновлён'
            self.stdout.write(self.style.SUCCESS(f'{action} пользователь: {email} ({role_name})'))

        self.stdout.write(self.style.SUCCESS('Готово'))


