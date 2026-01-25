from django.urls import path
from . import views

urlpatterns = [
    path('get-door-status/', views.get_door_status, name='get_door_status'), # The new poller
    path('get-pln-status/', views.get_pln_status, name='get_pln_status'),
]