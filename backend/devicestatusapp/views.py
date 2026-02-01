import json
from django.http import JsonResponse
from django.utils import timezone
from .models import DeviceState

# --- View untuk Get Status Pintu (Door Panel) ---
def get_door_status(request):
    if request.method == "GET":
        try:
            # PERBAIKAN: Gunakan .order_by('-last_updated')
            # Tanda minus (-) artinya DESCENDING (dari baru ke lama)
            device = DeviceState.objects.filter(device_name="Door Panel").order_by('-last_updated').first()
            
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Door Panel", "status": "Closed", "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status PLN ---
def get_pln_status(request):
    if request.method == "GET":
        try:
            # PERBAIKAN SAMA DISINI
            device = DeviceState.objects.filter(device_name="PLN").order_by('-last_updated').first()
            
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": "PLN",
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "PLN", "status": "Inactive", "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)