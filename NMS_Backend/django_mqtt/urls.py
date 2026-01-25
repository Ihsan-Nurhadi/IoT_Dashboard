from django.urls import path
from django.urls import include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('speakerapp.urls')),
    path('', include('dorlockapp.urls')),
    path('', include('rotaryapp.urls')),
    path('', include('floodlightapp.urls')),
    # path('', include('gps_tracer.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)