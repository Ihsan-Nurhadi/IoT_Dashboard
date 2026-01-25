import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "nayaka/ipsirine/command"

@csrf_exempt
def send_mqtt(request):
    if request.method == "POST":
        data = json.loads(request.body)

        # Ambil data
        device = data.get("device")
        client = data.get("client")
        speaker = data.get("speaker")
        volume = data.get("volume")

        # Buat JSON payload ke MQTT
        payload = json.dumps({
            "device": device,
            "client": client,
            "speaker": speaker,
            "volume": volume
        })

        # Publish
        client_mqtt = mqtt.Client()
        client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        client_mqtt.publish(MQTT_TOPIC, payload, qos=1)
        client_mqtt.disconnect()

        return JsonResponse({"status": "success", "sent": payload})

    return JsonResponse({"error": "POST only"}, status=405)


def index(request):
    return render(request, 'dashboard_app.html')
@csrf_exempt
def test_api(request):
    return JsonResponse({"message": "Hello from Django API"})