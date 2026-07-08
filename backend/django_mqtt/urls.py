from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from devicestatusapp import views as dorlock_views
from rotaryapp import views as rotary_views
from floodlightapp import views as floodlight_views

urlpatterns = [
    path('api/', include('speakerapp.urls')),
    path('api/get-door-status/', dorlock_views.get_door_status, name='get_door_status'),
    path('api/get-pln-status/', dorlock_views.get_pln_status, name='get_pln_status'),
    path('api/get-motion1-status/', dorlock_views.get_motion1_status, name='get_motion1_status'),
    path('api/get-motion2-status/', dorlock_views.get_motion2_status, name='get_motion2_status'),
    path('api/send-rotary/', rotary_views.send_mqtt, name='send_mqtt'),
    path('api/send-floodlight/', floodlight_views.floodlight_mqtt, name='floodlight_mqtt'),
    # path('', include('gps_tracer.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)