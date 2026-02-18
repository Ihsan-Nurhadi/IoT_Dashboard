import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render

# Konfigurasi Broker Baru
MQTT_BROKER = "202.155.90.125"
MQTT_PORT = 1883
MQTT_TOPIC = "ny/command/tower/nms"
MQTT_USER = "sensor"
MQTT_PASSWORD = "Naya@client123"
# MQTT_TOPIC_DATA = "ny/data/tower/nms" # Digunakan jika Anda ingin subscribe

@csrf_exempt
def send_mqtt(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Ambil data dari payload React
            device = data.get("device", "site_1")
            playlist = data.get("playlist")
            volume = data.get("volume")

            # Susun payload JSON tanpa spasi (minified)
            payload_dict = {
                "device": device,
                "playList": int(playlist),
                "volume": int(volume)
            }
            payload = json.dumps(payload_dict, separators=(',', ':'))
            client = mqtt.Client()
            if MQTT_USER and MQTT_PASSWORD:
                client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.publish(MQTT_TOPIC, payload, qos=1)
            client.disconnect()

            return JsonResponse({
                "status": "success", 
                "topic": MQTT_TOPIC,
                "sent_payload": payload
            })
        
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"error": "POST only"}, status=405)

def index(request):
    return render(request, 'dashboard_app.html')

@csrf_exempt
def test_api(request):
    return JsonResponse({"message": "Hello from Django API"})