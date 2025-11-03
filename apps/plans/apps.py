from django.apps import AppConfig


class PlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.plans'
    verbose_name = 'Планы'
    
    def ready(self):
        """Подключение сигналов при загрузке приложения"""
        import apps.plans.signals  # noqa

