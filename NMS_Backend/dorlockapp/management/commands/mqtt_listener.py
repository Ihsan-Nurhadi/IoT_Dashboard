# your_app/management/commands/mqtt_listener.py
import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from dorlockapp.models import DeviceState # Sesuaikan nama app

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door and PLN'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD
        TOPIC = settings.MQTT_TOPIC_DATA 

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"Connected! Subscribing to {TOPIC}"))
                client.subscribe(TOPIC)
            else:
                self.stdout.write(self.style.ERROR(f"Connection failed: {rc}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode()
                # Contoh: {"device_id":"NMS_002","ts":...,"data":{"door":"OPEN","pln":"ON"}}
                payload = json.loads(payload_str)
                data_obj = payload.get("data", {})

                # --- 1. PROSES STATUS PINTU ---
                door_status = data_obj.get("door")
                if door_status:
                    DeviceState.objects.update_or_create(
                        device_name="Door Panel",
                        defaults={'status': door_status} # "OPEN" / "CLOSED"
                    )
                    self.stdout.write(f"Updated Door: {door_status}")

                # --- 2. PROSES STATUS PLN ---
                pln_status = data_obj.get("pln")
                if pln_status:
                    # Mapping: Jika "ON" simpan "Active", jika "OFF" simpan "Inactive" (Opsional)
                    # Atau simpan mentah "ON"/"OFF"
                    final_pln = "Active" if pln_status == "ON" else "Inactive"
                    
                    DeviceState.objects.update_or_create(
                        device_name="PLN",
                        defaults={'status': final_pln} 
                    )
                    self.stdout.write(f"Updated PLN: {final_pln}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))

        client = mqtt.Client()
        client.username_pw_set(USER, PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error: {e}"))