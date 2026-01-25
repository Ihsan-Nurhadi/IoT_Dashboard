from . import views
from django.urls import path
from django.shortcuts import render
from .views import classify_site

urlpatterns = [
    path("", lambda r: render(r, "camera.html")),
    path("ptz/", views.ptz_control),
    path("ptz2/", views.ptz_control2),
    path('camera/connect/', views.connect_camera, name='connect_camera'),
    path('camera/connect2/', views.connect_camera2, name='connect_camera2'),    
    path("stream/", views.video_stream),
    path("stream2/", views.video_stream2), # Tambahan untuk stream2 jika dihapus
    path("notifications/", views.check_notifications, name="check_notifications"),
    path("camera/screenshot/", views.camera_screenshot, name="camera_screenshot"),
    path("classify/", classify_site),
]