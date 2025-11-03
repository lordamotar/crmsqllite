from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

User = settings.AUTH_USER_MODEL


class Plan(models.Model):
    """
    План на отдел (шаблон/контейнер). Начальник создает план
    и указывает дату начала/конца. Затем делает распределение по менеджерам
    через PlanAssignment.
    """
    name = models.CharField(
        'Название плана',
        max_length=200,
        help_text='Например: "План июнь 2025"'
    )
    description = models.TextField('Описание', blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_plans',
        verbose_name='Создал'
    )
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата изменения', auto_now=True)
    
    class Meta:
        db_table = 'plans'
        verbose_name = 'План'
        verbose_name_plural = 'Планы'
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.start_date} — {self.end_date})'
    
    def clean(self):
        """Валидация модели"""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError(
                    'Дата начала не может быть позже даты окончания'
                )
    
    def save(self, *args, **kwargs):
        """Сохранение с валидацией"""
        self.full_clean()
        super().save(*args, **kwargs)


class PlanAssignment(models.Model):
    """
    Назначение плана конкретному менеджеру.
    Условия исполнения (criteria_operator):
      - both = нужно достичь и по кол-ву и по сумме
      - either = достаточно одного из критериев
    """
    CRITERIA_OPERATOR_CHOICES = [
        ('both', 'Оба критерия (кол-во и сумма)'),
        ('either', 'Любой критерий (кол-во или сумма)'),
    ]
    
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name='План'
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='plan_assignments',
        verbose_name='Менеджер'
    )
    target_count = models.PositiveIntegerField(
        'Целевое количество заказов',
        default=0
    )
    target_sum = models.DecimalField(
        'Целевая сумма',
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    criteria_operator = models.CharField(
        'Условие выполнения',
        max_length=10,
        choices=CRITERIA_OPERATOR_CHOICES,
        default='both'
    )
    # Кэш прогресса
    achieved_count = models.PositiveIntegerField(
        'Достигнуто заказов',
        default=0
    )
    achieved_sum = models.DecimalField(
        'Достигнутая сумма',
        max_digits=18,
        decimal_places=2,
        default=0
    )
    is_achieved = models.BooleanField('Выполнен', default=False)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата изменения', auto_now=True)
    
    class Meta:
        db_table = 'plan_assignments'
        verbose_name = 'Назначение плана'
        verbose_name_plural = 'Назначения планов'
        unique_together = [['plan', 'manager']]
        indexes = [
            models.Index(fields=['plan', 'manager']),
            models.Index(fields=['manager', 'is_achieved']),
        ]
    
    def __str__(self):
        return f'{self.manager.short_name} — {self.plan.name}'
    
    def evaluate(self):
        """
        Возвращает tuple (achieved_bool, achieved_count, achieved_sum)
        но не сохраняет автоматически. Для сохранения вызвать save() после обновления полей.
        План считается выполненным, если количество заказов со статусом 'completed'
        равно или превышает целевое количество (target_count).
        """
        # План выполнен, если количество completed заказов >= target_count
        achieved = self.achieved_count >= self.target_count
        return achieved, self.achieved_count, self.achieved_sum
    
    def clean(self):
        """Валидация модели"""
        # Проверка, что начальник может назначать план подчиненному
        if self.plan and self.plan.created_by and self.manager:
            if not self.plan.created_by.is_manager_of(self.manager):
                raise ValidationError(
                    f'Вы можете назначать планы только своим подчиненным. '
                    f'{self.manager.short_name} не является вашим подчиненным.'
                )

