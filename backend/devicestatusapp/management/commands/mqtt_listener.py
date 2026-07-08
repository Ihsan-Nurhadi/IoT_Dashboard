# your_app/management/commands/mqtt_listener.py
import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from devicestatusapp.models import DeviceState

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door, PLN, and Motion Sensors'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD
        TOPIC = settings.MQTT_TOPIC_PUB2 

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"Connected! Subscribing to {TOPIC} and /matalite-test/sensor/#"))
                client.subscribe(TOPIC)
                client.subscribe("/matalite-test/sensor/#")
            else:
                self.stdout.write(self.style.ERROR(f"Connection failed: {rc}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode().strip()
                self.stdout.write(f"Received message: {payload_str}")

                # 1. Cek apakah ini command string langsung dari migration.md
                if payload_str == "MOTION1DETECTED":
                    DeviceState.objects.update_or_create(
                        device_name="Motion Sensor 1",
                        defaults={'status': 'Detected'}
                    )
                    self.stdout.write("Updated Motion Sensor 1: Detected")
                elif payload_str == "MOTION2DETECTED":
                    DeviceState.objects.update_or_create(
                        device_name="Motion Sensor 2",
                        defaults={'status': 'Detected'}
                    )
                    self.stdout.write("Updated Motion Sensor 2: Detected")
                elif payload_str == "MOTIONSTANDBY":
                    DeviceState.objects.update_or_create(
                        device_name="Motion Sensor 1",
                        defaults={'status': 'Standby'}
                    )
                    DeviceState.objects.update_or_create(
                        device_name="Motion Sensor 2",
                        defaults={'status': 'Standby'}
                    )
                    self.stdout.write("Updated Motion Sensor 1 & 2: Standby")
                else:
                    # 2. Cek apakah format JSON (backward compatibility)
                    try:
                        payload = json.loads(payload_str)
                        data_obj = payload.get("data", {})

                        # --- PROSES STATUS PINTU ---
                        door_status = data_obj.get("door")
                        if door_status:
                            DeviceState.objects.update_or_create(
                                device_name="Door Panel",
                                defaults={'status': door_status}
                            )
                            self.stdout.write(f"Updated Door: {door_status}")

                        # --- PROSES STATUS PLN ---
                        pln_status = data_obj.get("pln")
                        if pln_status:
                            final_pln = "Active" if pln_status == "ON" else "Inactive"
                            DeviceState.objects.update_or_create(
                                device_name="PLN",
                                defaults={'status': final_pln}
                            )
                            self.stdout.write(f"Updated PLN: {final_pln}")
                    except json.JSONDecodeError:
                        self.stdout.write(f"Unknown payload format: {payload_str}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))

        client = mqtt.Client()
        if USER and PASSWORD:
            client.username_pw_set(USER, PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error: {e}"))