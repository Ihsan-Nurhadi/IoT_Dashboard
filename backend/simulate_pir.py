import sys
import json
import time
import os

# Set Django environment to access settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_mqtt.settings")
import django
django.setup()

from django.conf import settings
import paho.mqtt.client as mqtt

def run_simulation(state_arg=None):
    # Default topic from whitebox node
    topic = "nms/E32_WB_TBGTEST/whitebox/motion_pir"
    
    # Tentukan state sensor
    if state_arg in ["alarm", "danger", "kabel", "kabel_dicabut", "0,0,0", "0"]:
        s = [0, 0, 0]
        desc = "KABEL DICABUT / ALARM (0, 0, 0)"
    elif state_arg in ["normal", "safe", "1,0,0", "1"]:
        s = [1, 0, 0]
        desc = "NORMAL (1, 0, 0)"
    elif state_arg:
        try:
            s = [int(x.strip()) for x in state_arg.split(",")]
            desc = f"CUSTOM ({s})"
        except Exception:
            s = [1, 0, 0]
            desc = "NORMAL DEFAULT (1, 0, 0)"
    else:
        s = [1, 0, 0]
        desc = "NORMAL DEFAULT (1, 0, 0)"

    payload = {
        "ip":"192.168.1.205",
        "ts":int(time.time()),
        "s":s
    }
    payload_str = json.dumps(payload)

    print(f"=== SIMULASI SENSOR PIR WHITEBOX ===")
    print(f"Kondisi  : {desc}")
    print(f"Broker   : {settings.MQTT_SERVER}:{settings.MQTT_PORT}")
    print(f"Topic    : {topic}")
    print(f"Payload  : {payload_str}")

    client_id = f"pir_sim_{int(time.time())}"
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id)
    except (AttributeError, TypeError):
        try:
            client = mqtt.Client(client_id)
        except Exception:
            client = mqtt.Client()
    if settings.MQTT_USER and settings.MQTT_PASSWORD:
        client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)

    try:
        client.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
        client.publish(topic, payload_str, qos=0)
        time.sleep(0.5)
        client.disconnect()
        print(f"[BERHASIL] Pesan PIR berhasil dikirim ke broker!\n")
        if s == [0, 0, 0]:
            print("Periksa terminal 'mqtt_listener' -> Anda akan melihat pesan:")
            print("[ALARM SIRINE] Kondisi bahaya PIR terdeteksi (s=[0, 0, 0])! Mentargetkan sirine relay 10s...")
            print("Command terkirim: {\"relay\": {\"state\": true, \"timeout_ms\": 10000}}")
        else:
            print("Periksa terminal 'mqtt_listener' -> Anda akan melihat kondisi [PIR Normal].")
    except Exception as e:
        print(f"[GAGAL] Error saat koneksi atau publish ke MQTT: {e}")

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "normal"
    run_simulation(arg)
