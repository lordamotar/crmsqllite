from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def timeclock_page(request):
    """Страница табеля учёта рабочего времени."""
    return render(request, 'timeclock/timeclock.html')

