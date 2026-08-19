from django.contrib import admin
from .models import SensorData, CableHealthTelemetry


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'wind_speed', 'wind_speed_ms', 'pitch', 'roll', 'tilt_rate', 'sway', 'total_tilt']
    list_filter = ['timestamp']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']


@admin.register(CableHealthTelemetry)
class CableHealthTelemetryAdmin(admin.ModelAdmin):
    list_display = ['id', 'device_id', 'timestamp', 'vibration', 'tension', 'impact', 'is_cut', 'temperature', 'device_status']
    list_filter = ['timestamp', 'device_status', 'is_cut', 'is_connected']
    search_fields = ['device_id']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

