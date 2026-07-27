from django.urls import path
from . import views

urlpatterns = [
    path('sensor-data/', views.SensorDataListCreateView.as_view(), name='sensor-data-list'),
    path('sensor-data/latest/', views.sensor_data_latest, name='sensor-data-latest'),
    path('sensor-data/history/', views.sensor_data_history, name='sensor-data-history'),
    path('sensor-data/sites-status/', views.sensor_data_sites_status, name='sensor-data-sites-status'),
    path('sensor-data/sites-visibility/', views.SiteVisibilityView.as_view(), name='sensor-data-sites-visibility'),
    path('sensor-data/sites/', views.SiteListCreateView.as_view(), name='site-list'),
    path('sensor-data/sites/<str:pk>/', views.SiteRetrieveUpdateDestroyView.as_view(), name='site-detail'),
]
