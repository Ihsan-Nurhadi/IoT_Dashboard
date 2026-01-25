from . import views
from django.urls import path


urlpatterns = [
    path('send-rotary/', views.send_mqtt, name='send_mqtt'),
]