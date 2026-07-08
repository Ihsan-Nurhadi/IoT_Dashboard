import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re
from django.shortcuts import render
from django.conf import settings

@csrf_exempt
def send_mqtt(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            command = data.get("command")
            
            if not command:
                # Fallback untuk format payload lama
                speaker_val = data.get("speaker")
                if speaker_val:
                    match = re.search(r'\d+', str(speaker_val))
                    if match:
                        command = f"SIREN{match.group(0)}ON"
                    else:
                        command = "SIREN#OFF"
                else:
                    command = "SIREN#OFF"

            # Publish ke MQTT broker baru di topic settings.MQTT_TOPIC_SUB (/matalite-test/in/)
            client_mqtt = mqtt.Client()
            if settings.MQTT_USER and settings.MQTT_PASSWORD:
                client_mqtt.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)

            client_mqtt.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
            client_mqtt.publish(settings.MQTT_TOPIC_SUB, command, qos=1)
            client_mqtt.disconnect()

            return JsonResponse({"status": "success", "sent": command})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "POST only"}, status=405)


def index(request):
    return render(request, 'dashboard_app.html')
@csrf_exempt
def test_api(request):
    return JsonResponse({"message": "Hello from Django API"})