from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class UserProfile(models.Model):
    """Профиль пользователя - расширение данных из таблицы users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Дополнительные поля профиля (не дублируем поля из User)
    bio = models.TextField(max_length=500, blank=True, verbose_name='О себе')
    website = models.URLField(blank=True, null=True, verbose_name='Веб-сайт')
    social_links = models.JSONField(default=dict, blank=True, verbose_name='Социальные сети')
    
    # Настройки интерфейса
    language = models.CharField(max_length=20, default='ru', verbose_name='Язык')
    timezone = models.CharField(max_length=50, default='Asia/Almaty', verbose_name='Часовой пояс')
    currency = models.CharField(max_length=10, default='KZT', verbose_name='Валюта')
    theme = models.CharField(max_length=20, default='light', verbose_name='Тема')
    
    # Настройки уведомлений
    email_notifications = models.BooleanField(default=True, verbose_name='Email уведомления')
    sms_notifications = models.BooleanField(default=False, verbose_name='SMS уведомления')
    push_notifications = models.BooleanField(default=True, verbose_name='Push уведомления')
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
        db_table = 'user_profile'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username}'
