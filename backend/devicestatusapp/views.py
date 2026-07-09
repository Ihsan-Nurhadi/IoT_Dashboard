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

# --- View untuk Get Status Motion Sensor 1 ---
def get_motion1_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 1").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 1", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status Motion Sensor 2 ---
def get_motion2_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 2").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 2", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Streaming CCTV RTSP (Integrasi Lokal) ---
import cv2
import time
from django.http import StreamingHttpResponse

def gen_cctv():
    import os
    # Paksa RTSP menggunakan TCP (bukan UDP) agar tidak ada packet loss di jalur VPN
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    rtsp_url = "rtsp://admin:BWIJZS@10.10.4.89:554/h264/ch1/main/av_stream"
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(rtsp_url)
                continue
            
            # Perkecil resolusi agar beban CPU lokal & bandwidth lebih ringan
            h, w = frame.shape[:2]
            if w > 1280:
                frame = cv2.resize(frame, (1280, int(h * (1280 / w))))
                
            # Encode frame ke JPEG dengan kualitas 70%
            _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            
            # Batasi frame rate ke kisaran ~25 FPS agar tidak menghabiskan daya CPU
            time.sleep(0.04)
    finally:
        cap.release()

def cctv_stream(request):
    try:
        return StreamingHttpResponse(gen_cctv(), content_type="multipart/x-mixed-replace;boundary=frame")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)