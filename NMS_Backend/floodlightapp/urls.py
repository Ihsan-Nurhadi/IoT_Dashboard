from . import views
from django.urls import path


urlpatterns = [
    path('send-floodlight/', views.floodlight_mqtt, name='floodlight_mqtt'),
]