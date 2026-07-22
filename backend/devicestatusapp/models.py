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