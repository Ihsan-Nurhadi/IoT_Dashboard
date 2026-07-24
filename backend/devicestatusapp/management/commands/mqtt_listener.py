import json
import os
import time
import threading
import cv2
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from devicestatusapp.models import DeviceState, DoorStatusLog

LAST_PIR_SNAPSHOT_TIME = 0.0
PIR_SNAPSHOT_COOLDOWN = 15.0

def trigger_pir_cctv_snapshot(stdout=None):
    global LAST_PIR_SNAPSHOT_TIME
    now_time = time.time()
    if now_time - LAST_PIR_SNAPSHOT_TIME < PIR_SNAPSHOT_COOLDOWN:
        return
    LAST_PIR_SNAPSHOT_TIME = now_time

    def run_capture():
        output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
        os.makedirs(output_dir, exist_ok=True)

        cameras = [
            ("cctv", "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"),
            ("cctv2", "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"),
        ]

        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        for camera_id, rtsp_url in cameras:
            try:
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    if stdout:
                        stdout.write(f"[PIR Snapshot] Failed to open RTSP stream for {camera_id}")
                    continue

                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                captured = False
                # Try for up to 3 seconds (6 attempts x 0.5s) to allow RTSP I-frame keyframe decoding
                for check_idx in range(6):
                    for _ in range(10):
                        cap.grab()
                    ret, frame = cap.retrieve()
                    if ret and frame is not None:
                        now = timezone.localtime(timezone.now())
                        timestamp = now.strftime('%Y%m%d_%H%M%S')
                        filename = f"{camera_id}_pir_{timestamp}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, frame)
                        if stdout:
                            stdout.write(f"[PIR Snapshot] Successfully saved {filename}")
                        captured = True
                        break
                    time.sleep(0.5)

                cap.release()
                if not captured and stdout:
                    stdout.write(f"[PIR Snapshot] Could not retrieve frame from {camera_id}")

            except Exception as err:
                if stdout:
                    stdout.write(f"[PIR Snapshot Error] {camera_id}: {err}")

    threading.Thread(target=run_capture, daemon=True).start()

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door, PLN, and Motion Sensors'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD

        TOPIC_BLACKBOX = "nms/E32_WB_WS/whitebox/#"
        TOPIC_SPEAKER = "nms/esp32-speaker-003734fe8ce0/speaker/#"
        TOPIC_PIR = "nms/E32_PIR_WS/pir/#"

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"[MQTT] Connected! Subscribing to {TOPIC_BLACKBOX}, {TOPIC_SPEAKER}, {TOPIC_PIR}"))
                client.subscribe(TOPIC_BLACKBOX)
                client.subscribe(TOPIC_SPEAKER)
                client.subscribe(TOPIC_PIR)
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

                            now_time = timezone.now()
                            dev, created = DeviceState.objects.get_or_create(
                                device_name="Door Panel",
                                defaults={'status': status_val, 'last_updated': now_time}
                            )
                            if created or dev.status != status_val:
                                DoorStatusLog.objects.create(status=log_status)
                                self.stdout.write(f"Updated Door Panel & Logged Event: {log_status}")
                            
                            dev.status = status_val
                            dev.last_updated = now_time
                            dev.save()
                            
                    # 2. Power (PLN) status -> nms/E32_WB_WS/whitebox/device_power
                    elif msg.topic.endswith("/device_power"):
                        mains_present = payload.get("mains")
                        if mains_present is not None:
                            status_val = "Active" if mains_present else "Inactive"
                            now_time = timezone.now()
                            dev, created = DeviceState.objects.get_or_create(
                                device_name="PLN",
                                defaults={'status': status_val, 'last_updated': now_time}
                            )
                            dev.status = status_val
                            dev.last_updated = now_time
                            dev.save()
                            self.stdout.write(f"Updated PLN: {status_val}")
                            
                    # 3. Motion (PIR) status -> ONLY nms/E32_PIR_WS/pir/#
                    elif "/pir/" in msg.topic:
                        s_arr = payload.get("s")
                        if isinstance(s_arr, list):
                            has_detection = False
                            now_time = timezone.now()
                            for idx, val in enumerate(s_arr):
                                if val is not None:
                                    is_detected = str(val).strip().lower() in ["1", "true"]
                                    if is_detected:
                                        has_detection = True
                                    sensor_name = f"Motion Sensor {idx + 1}"
                                    sensor_val = "Detected" if is_detected else "Standby"
                                    
                                    dev, _ = DeviceState.objects.get_or_create(
                                        device_name=sensor_name,
                                        defaults={'status': sensor_val, 'last_updated': now_time}
                                    )
                                    dev.status = sensor_val
                                    dev.last_updated = now_time
                                    dev.save()
                                    self.stdout.write(f"Updated {sensor_name}: {sensor_val} at {now_time.strftime('%H:%M:%S')}")

                            if has_detection:
                                self.stdout.write("[PIR] Motion detected! Triggering CCTV snapshot...")
                                trigger_pir_cctv_snapshot(self.stdout)
                                
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
