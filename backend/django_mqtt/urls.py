from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from devicestatusapp import views as dorlock_views
from rotaryapp import views as rotary_views
from monitoring import views as monitoring_views

urlpatterns = [
    path('api/', include('speakerapp.urls')),
    path('api/get-door-status/', dorlock_views.get_door_status, name='get_door_status'),
    path('api/get-pln-status/', dorlock_views.get_pln_status, name='get_pln_status'),
    path('api/get-motion1-status/', dorlock_views.get_motion1_status, name='get_motion1_status'),
    path('api/get-motion2-status/', dorlock_views.get_motion2_status, name='get_motion2_status'),
    path('api/get-motion3-status/', dorlock_views.get_motion3_status, name='get_motion3_status'),
    path('api/get-motion4-status/', dorlock_views.get_motion4_status, name='get_motion4_status'),
    path('api/send-rotary/', rotary_views.send_mqtt, name='send_mqtt'),
    path('api/cctv-stream/', dorlock_views.cctv_stream, name='cctv_stream'),
    path('api/cctv/capture-photo/', dorlock_views.capture_photo, name='capture_photo'),
    path('api/cctv/capture-video/', dorlock_views.capture_video, name='capture_video'),
    path('api/cctv/latest/', dorlock_views.cctv_latest, name='cctv_latest'),
    path('api/cctv/history/', dorlock_views.cctv_history, name='cctv_history'),
    path('api/cctv/alerts/', dorlock_views.cctv_alerts, name='cctv_alerts'),
    path('api/cctv/detection-logs/', dorlock_views.cctv_detection_logs, name='cctv_detection_logs'),
    path('api/door-logs/', dorlock_views.get_door_logs, name='get_door_logs'),
    path('api/verticality/', include('monitoring.urls')),
    path('api/sensor-readings/latest/', monitoring_views.LatestReadingView.as_view(), name='sensor-latest'),
    path('api/sensor-readings/history/', monitoring_views.SensorHistoryView.as_view(), name='sensor-history'),
    path('api/sensor-readings/ingest/', monitoring_views.IngestSensorReadingView.as_view(), name='sensor-ingest'),
    path('api/ble/latest/', monitoring_views.ble_latest_scans, name='ble-latest'),
    path('api/ble/history/', monitoring_views.ble_history_chart, name='ble-history'),
    path('api/ble/alerts/', monitoring_views.ble_alerts, name='ble-alerts'),
    path('api/ble/history-logs/', monitoring_views.ble_history_logs, name='ble-history-logs'),
    path('api/rfid/latest/', monitoring_views.rfid_latest_scans, name='rfid-latest'),
    path('api/rfid/history-logs/', monitoring_views.rfid_history_logs, name='rfid-history-logs'),

    
    # Auth endpoints
    path('api/auth/login/', monitoring_views.api_login, name='api-login'),
    path('api/auth/logout/', monitoring_views.api_logout, name='api-logout'),
    path('api/auth/status/', monitoring_views.api_auth_status, name='api-auth-status'),

    # BLE Devices config endpoints
    path('api/ble/devices/', monitoring_views.ble_devices_list, name='ble-devices-list'),
    path('api/ble/devices/<str:mac>/', monitoring_views.ble_device_detail, name='ble-device-detail'),
    path('api/ble/devices/<str:mac>/delete/', monitoring_views.ble_device_delete_post, name='ble-device-delete-post'),
    path('api/ble/devices/scanned-unregistered/', monitoring_views.ble_unregistered_list, name='ble-unregistered-list'),

    # CCTV Cameras config endpoints
    path('api/cameras/', dorlock_views.cameras_list, name='cameras-list'),
    path('api/cameras/create/', dorlock_views.camera_create, name='camera-create'),
    path('api/cameras/<str:camera_id>/', dorlock_views.camera_detail, name='camera-detail'),
    path('api/cameras/<str:camera_id>/update/', dorlock_views.camera_update, name='camera-update'),
    path('api/cameras/<str:camera_id>/delete/', dorlock_views.camera_delete, name='camera-delete'),
    path('api/cameras/<str:camera_id>/snapshot/', dorlock_views.camera_snapshot, name='camera-snapshot'),
    path('api/cctv/baselines-status/', dorlock_views.get_baselines_status, name='baselines_status'),
    path('api/cctv/capture-baseline/', dorlock_views.capture_baseline, name='capture_baseline'),
    path('api/cctv/delete-baseline/', dorlock_views.delete_baseline, name='delete_baseline'),
    # path('', include('gps_tracer.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)