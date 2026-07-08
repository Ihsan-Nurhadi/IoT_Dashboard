from django.urls import path
from . import views

urlpatterns = [
    path('get-door-status/', views.get_door_status, name='get_door_status'), # The new poller
    path('get-pln-status/', views.get_pln_status, name='get_pln_status'),
    path('get-motion1-status/', views.get_motion1_status, name='get_motion1_status'),
    path('get-motion2-status/', views.get_motion2_status, name='get_motion2_status'),
]