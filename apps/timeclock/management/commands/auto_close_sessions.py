from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time as dtime
from apps.timeclock.models import WorkSession


class Command(BaseCommand):
    help = 'Автоматически закрывает неактивные сессии после 18:00'

    def handle(self, *args, **options):
        now = timezone.localtime()
        if now.time() < dtime(hour=18, minute=0):
            self.stdout.write(self.style.WARNING('Слишком рано, автозакрытие работает после 18:00'))
            return

        cutoff = now - timedelta(minutes=20)
        sessions = WorkSession.objects.filter(is_closed=False)
        updated = []

        for s in sessions:
            if s.start_time.date() != now.date():
                continue
            if not s.last_activity:
                s.close(end_time=now)
                updated.append(s.id)
                continue
            if s.last_activity <= cutoff:
                end_time = s.last_activity + timedelta(minutes=20)
                s.close(end_time=end_time)
                updated.append(s.id)

        if updated:
            self.stdout.write(self.style.SUCCESS(f'Закрыто сессий: {len(updated)}'))
        else:
            self.stdout.write('Нет сессий для закрытия')

