from django.contrib import admin
from .models import CCTVCamera

@admin.register(CCTVCamera)
class CCTVCameraAdmin(admin.ModelAdmin):
    list_display = ('camera_name', 'camera_id', 'is_active', 'morning_start', 'morning_end', 'afternoon_start', 'afternoon_end', 'night_start', 'night_end')
    search_fields = ('camera_name', 'camera_id')
    list_filter = ('is_active',)
    fieldsets = (
        ('Info Kamera', {
            'fields': ('camera_id', 'camera_name', 'is_active')
        }),
        ('Koneksi Stream', {
            'fields': ('rtsp_url', 'onvif_url', 'username', 'password', 'width', 'height')
        }),
        ('Titik Koordinat', {
            'fields': ('detection_zones',)
        }),
        ('Konfigurasi Rentang Jam Baseline (TOD)', {
            'description': 'Tentukan jam mulai dan jam selesai untuk masing-masing baseline (0 s.d. 23).',
            'fields': (
                ('morning_start', 'morning_end'),
                ('afternoon_start', 'afternoon_end'),
                ('night_start', 'night_end')
            )
        }),
    )

