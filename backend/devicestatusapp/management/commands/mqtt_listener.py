# your_app/management/commands/mqtt_listener.py
import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from devicestatusapp.models import DeviceState

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door, PLN, and Motion Sensors'

    def handle(self, *args, **kwargs):
        # Broker 1 settings (Old Broker)
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD
        TOPIC = settings.MQTT_TOPIC_PUB2

        # Broker 2 settings (New Broker)
        NEW_BROKER = settings.NEW_MQTT_SERVER
        NEW_PORT = settings.NEW_MQTT_PORT
        NEW_USER = settings.NEW_MQTT_USER
        NEW_PASSWORD = settings.NEW_MQTT_PASSWORD
        NEW_TOPIC = "nms/raspi_FOKLENDER/blackbox/#"

        def on_connect_old(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"[Broker Lama] Connected! Subscribing to {TOPIC} and /matalite-test/sensor/#"))
                client.subscribe(TOPIC)
                client.subscribe("/matalite-test/sensor/#")
            else:
                self.stdout.write(self.style.ERROR(f"[Broker Lama] Connection failed: {rc}"))

        def on_message_old(client, userdata, msg):
            try:
                payload_str = msg.payload.decode().strip()
                self.stdout.write(f"[Broker Lama] Received message on {msg.topic}: {payload_str}")

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
                self.stdout.write(self.style.ERROR(f"[Broker Lama] Error: {e}"))

        def on_connect_new(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"[Broker Baru] Connected! Subscribing to {NEW_TOPIC}"))
                client.subscribe(NEW_TOPIC)
            else:
                self.stdout.write(self.style.ERROR(f"[Broker Baru] Connection failed: {rc}"))

        def on_message_new(client, userdata, msg):
            try:
                payload_str = msg.payload.decode().strip()
                self.stdout.write(f"[Broker Baru] Received message on {msg.topic}: {payload_str}")

                try:
                    payload = json.loads(payload_str)
                    
                    # 1. Door status -> nms/raspi_FOKLENDER/blackbox/door
                    if msg.topic.endswith("/door"):
                        is_open = payload.get("open")
                        if is_open is not None:
                            status_val = "Open" if is_open else "Closed"
                            DeviceState.objects.update_or_create(
                                device_name="Door Panel",
                                defaults={'status': status_val}
                            )
                            self.stdout.write(f"Updated Door Panel: {status_val}")
                            
                    # 2. Power (PLN) status -> nms/raspi_FOKLENDER/blackbox/device_power
                    elif msg.topic.endswith("/device_power"):
                        mains_present = payload.get("mains")
                        if mains_present is not None:
                            status_val = "Active" if mains_present else "Inactive"
                            DeviceState.objects.update_or_create(
                                device_name="PLN",
                                defaults={'status': status_val}
                            )
                            self.stdout.write(f"Updated PLN: {status_val}")
                            
                    # 3. Motion (PIR) status -> nms/raspi_FOKLENDER/blackbox/motion_pir
                    elif msg.topic.endswith("/motion_pir"):
                        s_arr = payload.get("s")
                        if isinstance(s_arr, list) and len(s_arr) >= 2:
                            # s[0] -> Motion Sensor 1
                            if s_arr[0] is not None:
                                s1_val = "Detected" if s_arr[0] == 1 else "Standby"
                                DeviceState.objects.update_or_create(
                                    device_name="Motion Sensor 1",
                                    defaults={'status': s1_val}
                                )
                                self.stdout.write(f"Updated Motion Sensor 1: {s1_val}")
                            # s[1] -> Motion Sensor 2
                            if s_arr[1] is not None:
                                s2_val = "Detected" if s_arr[1] == 1 else "Standby"
                                DeviceState.objects.update_or_create(
                                    device_name="Motion Sensor 2",
                                    defaults={'status': s2_val}
                                )
                                self.stdout.write(f"Updated Motion Sensor 2: {s2_val}")
                                
                except json.JSONDecodeError:
                    self.stdout.write(f"[Broker Baru] JSON Decode Error on payload: {payload_str}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[Broker Baru] Error: {e}"))

        # Setup Client (Unified Broker)
        client_new = mqtt.Client("django_subscriber_new")
        if NEW_USER and NEW_PASSWORD:
            client_new.username_pw_set(NEW_USER, NEW_PASSWORD)
        client_new.on_connect = on_connect_new
        client_new.on_message = on_message_new

        # Connect and Start loop_start
        try:
            self.stdout.write(f"Connecting to Broker: {NEW_BROKER}:{NEW_PORT}")
            client_new.connect(NEW_BROKER, NEW_PORT, 60)
            client_new.loop_start()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error (Broker): {e}"))

        # Keep main thread alive
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopping listener..."))
            client_new.loop_stop()