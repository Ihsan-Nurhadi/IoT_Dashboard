# your_app/management/commands/mqtt_listener.py
import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from devicestatusapp.models import DeviceState, DoorStatusLog

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door, PLN, and Motion Sensors'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD

        TOPIC_BLACKBOX = "nms/E32_WB_WS/whitebox/#"
        TOPIC_SPEAKER = "nms/esp32-speaker-003734fe8ce0/speaker/#"

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"[MQTT] Connected! Subscribing to {TOPIC_BLACKBOX} and {TOPIC_SPEAKER}"))
                client.subscribe(TOPIC_BLACKBOX)
                client.subscribe(TOPIC_SPEAKER)
            else:
                self.stdout.write(self.style.ERROR(f"[MQTT] Connection failed with code {rc}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode().strip()
                self.stdout.write(f"[MQTT] Received message on {msg.topic}: {payload_str}")

                try:
                    payload = json.loads(payload_str)
                    
                    # 1. Door status -> nms/E32_WB_WS/whitebox/door
                    if msg.topic.endswith("/door"):
                        is_open = payload.get("open")
                        if is_open is not None:
                            status_val = "Open" if is_open else "Closed"
                            log_status = "OPEN" if is_open else "CLOSE"

                            dev, created = DeviceState.objects.get_or_create(
                                device_name="Door Panel",
                                defaults={'status': status_val}
                            )
                            if created or dev.status != status_val:
                                dev.status = status_val
                                dev.save()
                                DoorStatusLog.objects.create(status=log_status)
                                self.stdout.write(f"Updated Door Panel & Logged Event: {log_status}")
                            else:
                                dev.save() # update last_updated timestamp
                                self.stdout.write(f"Door Panel status unchanged: {status_val}")
                            
                    # 2. Power (PLN) status -> nms/E32_WB_WS/whitebox/device_power
                    elif msg.topic.endswith("/device_power"):
                        mains_present = payload.get("mains")
                        if mains_present is not None:
                            status_val = "Active" if mains_present else "Inactive"
                            DeviceState.objects.update_or_create(
                                device_name="PLN",
                                defaults={'status': status_val}
                            )
                            self.stdout.write(f"Updated PLN: {status_val}")
                            
                    # 3. Motion (PIR) status -> nms/E32_WB_WS/whitebox/motion_pir
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
                                
                    # 4. Speaker status -> nms/esp32-speaker-003734fe8ce0/speaker/speaker
                    elif "/speaker/speaker" in msg.topic:
                        playing = payload.get("playing")
                        track = payload.get("track")
                        volume = payload.get("volume")
                        self.stdout.write(f"Speaker State: playing={playing}, track={track}, volume={volume}")

                except json.JSONDecodeError:
                    self.stdout.write(f"[MQTT] JSON Decode Error on payload: {payload_str}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[MQTT] Error: {e}"))

        client = mqtt.Client("django_subscriber_unified")
        if USER and PASSWORD:
            client.username_pw_set(USER, PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            self.stdout.write(f"Connecting to Broker: {BROKER}:{PORT}")
            client.connect(BROKER, PORT, 60)
            client.loop_start()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error (Broker): {e}"))

        # Keep main thread alive
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopping listener..."))
            client.loop_stop()
