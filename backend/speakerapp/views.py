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

            # Map command string to JSON format: {"track": "voiceX"}
            cmd_to_track = {
                "SIREN1ON": "voice1",
                "SIREN2ON": "voice2",
                "SIREN3ON": "voice3",
                "SIREN4ON": "voice4",
                "SIREN5ON": "voice5",
                "SIREN6ON": "voice6",
                "SIREN#OFF": "stop",
            }
            track_name = cmd_to_track.get(command, "stop")
            payload = {"track": track_name}
            payload_str = json.dumps(payload)

            # Publish ke MQTT broker baru di topic settings.MQTT_TOPIC_SUB (nms/raspi_FOKLENDER/blackbox/config)
            client_mqtt = mqtt.Client()
            if settings.MQTT_USER and settings.MQTT_PASSWORD:
                client_mqtt.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)

            client_mqtt.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
            client_mqtt.publish(settings.MQTT_TOPIC_SUB, payload_str, qos=1)
            client_mqtt.disconnect()

            return JsonResponse({"status": "success", "sent": payload})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "POST only"}, status=405)


def index(request):
    return render(request, 'dashboard_app.html')
@csrf_exempt
def test_api(request):
    return JsonResponse({"message": "Hello from Django API"})