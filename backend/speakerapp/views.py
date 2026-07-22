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
            volume = data.get("volume")
            
            speaker_payload = {}
            
            # 1. Parse volume if provided
            if volume is not None:
                try:
                    vol_int = int(volume)
                    if 0 <= vol_int <= 100:
                        speaker_payload["volume"] = vol_int
                except ValueError:
                    pass
            
            is_stop = False
            
            # 2. Parse command if provided
            if command:
                if command == "SIREN#OFF":
                    is_stop = True
                else:
                    match = re.match(r'SIREN([1-6])ON', command)
                    if match:
                        track_index = int(match.group(1))
                        speaker_payload["play"] = track_index
            
            # Fallback if neither command nor volume was found, but old speaker_val exists
            if not command and volume is None:
                speaker_val = data.get("speaker")
                if speaker_val:
                    match = re.search(r'\d+', str(speaker_val))
                    if match:
                        speaker_payload["play"] = int(match.group(0))
                    else:
                        is_stop = True

            if is_stop:
                payload = {"reset": {"action": True}}
            elif not speaker_payload:
                return JsonResponse({"error": "Invalid request. Provide command or volume."}, status=400)
            else:
                payload = {"speaker": speaker_payload}
                
            payload_str = json.dumps(payload)

            # Publish ke MQTT broker di topic settings.MQTT_TOPIC_SPEAKER_CONFIG
            client_mqtt = mqtt.Client()
            if settings.MQTT_USER and settings.MQTT_PASSWORD:
                client_mqtt.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)

            client_mqtt.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
            client_mqtt.publish(settings.MQTT_TOPIC_SPEAKER_CONFIG, payload_str, qos=1)
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