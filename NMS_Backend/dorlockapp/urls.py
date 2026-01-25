from django.urls import path
from . import views

urlpatterns = [
    path('api/get-door-status/', views.get_door_status, name='get_door_status'), # The new poller
    path('api/get-pln-status/', views.get_pln_status, name='get_pln_status'),
]