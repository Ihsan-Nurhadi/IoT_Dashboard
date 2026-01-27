import json
import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

MQTT_BROKER = "202.155.90.125"
MQTT_PORT = 1883
MQTT_TOPIC = "ny/command/tower/nms"
MQTT_USER = "sensor"
MQTT_PASSWORD = "Naya@client123"

@csrf_exempt
def send_mqtt(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body)
        state_value = data.get("state", data.get("status"))

        if state_value not in [1, 0]:
            return JsonResponse({"error": "Invalid state. Use 1 (ON) or 0 (OFF)"}, status=400)

        # 2. Susun Format JSON sesuai permintaan (Target Payload)
        payload_dict = {
            "device_id": "NMS_002",
            "cmd": "rotator",
            "state": state_value
        }
        
        # Ubah dict python ke JSON String
        payload_str = json.dumps(payload_dict)

        client = mqtt.Client()
        if MQTT_USER and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish(MQTT_TOPIC, payload_str, qos=1)
        client.disconnect()

        return JsonResponse({
            "status": "success",
            "mqtt_payload": payload_str
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
