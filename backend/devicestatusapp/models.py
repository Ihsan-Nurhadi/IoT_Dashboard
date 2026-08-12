# models.py
from django.db import models
from django.utils import timezone

class DeviceState(models.Model):
    device_name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50) # e.g., "Open", "Closed"
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.device_name}: {self.status}"

class DoorStatusLog(models.Model):
    status = models.CharField(max_length=50) # e.g., "OPEN", "CLOSE"
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.status}"

class CCTVCamera(models.Model):
    camera_id = models.CharField(max_length=50, unique=True) # e.g., 'cctv', 'cctv2'
    camera_name = models.CharField(max_length=100)
    rtsp_url = models.CharField(max_length=500)
    onvif_url = models.CharField(max_length=500, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=100, blank=True, null=True)
    width = models.IntegerField(default=1920)
    height = models.IntegerField(default=1080)
    is_active = models.BooleanField(default=True)
    detection_zones = models.TextField(default='[]') # JSON string stores list of zones with points & labels
    
    # Baseline hour configuration (Time of Day ranges)
    morning_start = models.IntegerField(default=6, help_text="Jam mulai baseline pagi (0-23)")
    morning_end = models.IntegerField(default=12, help_text="Jam selesai baseline pagi (0-23)")
    afternoon_start = models.IntegerField(default=12, help_text="Jam mulai baseline siang (0-23)")
    afternoon_end = models.IntegerField(default=18, help_text="Jam selesai baseline siang (0-23)")
    night_start = models.IntegerField(default=18, help_text="Jam mulai baseline malam (0-23)")
    night_end = models.IntegerField(default=6, help_text="Jam selesai baseline malam (0-23)")

    def __str__(self):
        return f"{self.camera_name} ({self.camera_id})"