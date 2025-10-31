from django.db import migrations, models


def set_default_role(apps, schema_editor):
    """Устанавливаем роль по умолчанию для пользователей без роли"""
    User = apps.get_model('accounts', 'User')
    Role = apps.get_model('accounts', 'Role')
    
    # Получаем или создаем роль admin
    admin_role, _ = Role.objects.get_or_create(
        name='admin',
        defaults={'description': 'Администратор системы'}
    )
    
    # Назначаем роль всем пользователям без роли
    User.objects.filter(role__isnull=True).update(role=admin_role)


def reverse_set_default_role(apps, schema_editor):
    """Обратная операция"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(set_default_role, reverse_set_default_role),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.ForeignKey(
                on_delete=models.PROTECT,
                related_name='users',
                to='accounts.role',
                verbose_name='Роль'
            ),
        ),
    ]
