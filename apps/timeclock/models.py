from django.db import models
from django.conf import settings
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class WorkSession(models.Model):
    """Одна рабочая сессия пользователя (обычно один рабочий день)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='work_sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    created_via = models.CharField(max_length=50, choices=(('auto', 'auto'), ('manual', 'manual')), default='auto')
    note = models.TextField(blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ('-start_time',)
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['is_closed', 'start_time']),
        ]

    def close(self, end_time=None):
        if self.is_closed:
            return
        if end_time is None:
            end_time = timezone.now()
        self.end_time = end_time
        self.is_closed = True
        self.save(update_fields=['end_time', 'is_closed'])

    def duration_seconds(self):
        if not self.end_time:
            return (timezone.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    def duration_hours(self):
        return round(self.duration_seconds() / 3600, 2)


class DutyAssignment(models.Model):
    """Назначение дежурного менеджера на конкретную дату."""

    date = models.DateField()
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duties')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_duties')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('date', 'manager')
        ordering = ('-date',)


class WorkDayMark(models.Model):
    """Ручная отметка дня в табеле (код: К/Б/А/О/В)."""

    CODE_CHOICES = (
        ('К', 'Командировка'),
        ('Б', 'Больничный'),
        ('А', 'Без содержания'),
        ('О', 'Отпуск'),
        ('В', 'Выходной'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workday_marks')
    date = models.DateField()
    code = models.CharField(max_length=1, choices=CODE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        indexes = [models.Index(fields=['user', 'date'])]
        ordering = ('-date',)

