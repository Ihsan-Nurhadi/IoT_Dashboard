from django.contrib import admin
from .models import SensorData


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'wind_speed', 'wind_speed_ms', 'pitch', 'roll', 'tilt_rate', 'sway', 'total_tilt']
    list_filter = ['timestamp']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
