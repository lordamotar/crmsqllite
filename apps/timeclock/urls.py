from django.urls import path
from . import views, views_pages


app_name = 'timeclock'


urlpatterns = [
    path('', views_pages.timeclock_page, name='timeclock_page'),
    path('start/', views.start_work, name='start'),
    path('stop/', views.stop_work, name='stop'),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
    path('status/', views.current_session_status, name='status'),
    path('my_sessions/', views.my_sessions, name='my_sessions'),
    path('marks/', views.get_marks, name='marks'),
    path('set_mark/', views.set_mark, name='set_mark'),
    path('export_xlsx/', views.export_timeclock_xlsx, name='export_xlsx'),
]

