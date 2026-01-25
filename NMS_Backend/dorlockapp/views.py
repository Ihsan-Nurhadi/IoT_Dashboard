import json
import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone  # <--- PENTING: Tambahkan import ini
from .models import DeviceState

# --- View untuk Get Status Pintu (Door Panel) ---
def get_door_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Door Panel").first()
            
            if device:
                # Konversi waktu server ke Waktu Lokal (Asia/Jakarta)
                local_time = timezone.localtime(device.last_updated)
                
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S") # Format jam lokal
                })
            else:
                return JsonResponse({
                    "device": "Door Panel", 
                    "status": "Closed",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status PLN ---
def get_pln_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="PLN").first()
            
            if device:
                # Konversi waktu server ke Waktu Lokal (Asia/Jakarta)
                local_time = timezone.localtime(device.last_updated)

                return JsonResponse({
                    "device": "PLN",
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S") # Format jam lokal
                })
            else:
                return JsonResponse({
                    "device": "PLN", 
                    "status": "Inactive",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)