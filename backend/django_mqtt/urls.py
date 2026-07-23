from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from devicestatusapp import views as dorlock_views
from rotaryapp import views as rotary_views

urlpatterns = [
    path('api/', include('speakerapp.urls')),
    path('api/get-door-status/', dorlock_views.get_door_status, name='get_door_status'),
    path('api/get-pln-status/', dorlock_views.get_pln_status, name='get_pln_status'),
    path('api/get-motion1-status/', dorlock_views.get_motion1_status, name='get_motion1_status'),
    path('api/get-motion2-status/', dorlock_views.get_motion2_status, name='get_motion2_status'),
    path('api/send-rotary/', rotary_views.send_mqtt, name='send_mqtt'),
    path('api/cctv-stream/', dorlock_views.cctv_stream, name='cctv_stream'),
    path('api/cctv/capture-photo/', dorlock_views.capture_photo, name='capture_photo'),
    path('api/cctv/capture-video/', dorlock_views.capture_video, name='capture_video'),
    path('api/cctv/latest/', dorlock_views.cctv_latest, name='cctv_latest'),
    path('api/cctv/history/', dorlock_views.cctv_history, name='cctv_history'),
    path('api/cctv/alerts/', dorlock_views.cctv_alerts, name='cctv_alerts'),
    path('api/door-logs/', dorlock_views.get_door_logs, name='get_door_logs'),
    # path('', include('gps_tracer.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)