# models.py
from django.db import models

class DeviceState(models.Model):
    device_name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50) # e.g., "Open", "Closed"
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device_name}: {self.status}"