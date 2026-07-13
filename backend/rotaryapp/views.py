import json
import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

@csrf_exempt
def send_mqtt(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        state_value = data.get("state", data.get("status"))

        if state_value not in [1, 0]:
            return JsonResponse({"error": "Invalid state. Use 1 (ON) or 0 (OFF)"}, status=400)

        # Susun command payload JSON sesuai kebutuhan node esp32-blackbox / bridge
        payload = {
            "relay": {
                "state": True if state_value == 1 else False
            }
        }
        payload_str = json.dumps(payload)

        client = mqtt.Client()
        if settings.MQTT_USER and settings.MQTT_PASSWORD:
            client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)

        client.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
        client.publish(settings.MQTT_TOPIC_SUB, payload_str, qos=1)
        client.disconnect()

        return JsonResponse({
            "status": "success",
            "mqtt_payload": payload_str
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

