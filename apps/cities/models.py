from django.db import models


class City(models.Model):
    """Модель города"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название города',
        unique=True
    )
    region = models.CharField(
        max_length=100,
        verbose_name='Регион',
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=100,
        verbose_name='Страна',
        default='Казахстан'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']

    def __str__(self):
        return self.name