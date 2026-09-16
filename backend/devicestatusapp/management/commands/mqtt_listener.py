import json
import os
import time
import threading
import cv2
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from devicestatusapp.models import DeviceState, DoorStatusLog, PowerStatusLog

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
                        now = timezone.now()
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
        self.last_siren_trigger_time = 0.0
        self.relay_active = False
        self.last_pir_s = None
        BROKER = settings.MQTT_SERVER
        PORT = settings.MQTT_PORT
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD

        TOPIC_BLACKBOX = "nms/E32_WB_TBGTEST/whitebox/#"
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
                            log_status = "ON" if mains_present else "OFF"
                            now_time = timezone.now()
                            dev, created = DeviceState.objects.get_or_create(
                                device_name="PLN",
                                defaults={'status': status_val, 'last_updated': now_time}
                            )
                            if created or dev.status != status_val:
                                PowerStatusLog.objects.create(status=log_status, timestamp=now_time)
                                self.stdout.write(f"Updated PLN & Logged Event: {log_status}")

                            dev.status = status_val
                            dev.last_updated = now_time
                            dev.save()
                            self.stdout.write(f"Updated PLN: {status_val}")
                            
                    # 3. Motion (PIR) status -> nms/.../whitebox/motion_pir OR /pir/
                    elif msg.topic.endswith("/motion_pir") or "/pir/" in msg.topic:
                        s_arr = payload.get("s")
                        if isinstance(s_arr, list):
                            has_detection = False
                            now_time = timezone.now()
                            normalized_s = []
                            for idx, val in enumerate(s_arr):
                                if val is not None:
                                    is_detected = str(val).strip().lower() in ["1", "true"]
                                    normalized_s.append(1 if is_detected else 0)
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

                            # Simulasi / Logika Alarm Prototipe:
                            # Jika PIR bernilai [0, 0, 0] (atau semua sensor 0) -> Trigger sirine relay timeout 10 detik
                            # Jika PIR bernilai normal e.g. [1, 0, 0] -> Status normal
                            is_alarm_triggered = len(normalized_s) > 0 and all(x == 0 for x in normalized_s)
                            is_state_transition = (self.last_pir_s != normalized_s)
                            self.last_pir_s = normalized_s

                            if is_alarm_triggered:
                                current_epoch = time.time()
                                # Trigger sirine jika:
                                # 1. Relay saat ini sedang MATI (sudah selesai timeout 10s), ATAU
                                # 2. Terjadi perubahan status baru (misal dari normal 1,0,0 ke 0,0,0), ATAU
                                # 3. Sudah lewat jeda 10 detik
                                should_trigger = (not self.relay_active) or is_state_transition or (current_epoch - self.last_siren_trigger_time >= 10.0)

                                if should_trigger:
                                    self.last_siren_trigger_time = current_epoch
                                    self.relay_active = True
                                    self.stdout.write(self.style.WARNING(f"[ALARM SIRINE] Kondisi bahaya PIR terdeteksi (s={normalized_s})! Mentargetkan sirine relay 10s..."))
                                    
                                    relay_cmd = json.dumps({"relay": {"state": True, "timeout_ms": 10000}})
                                    
                                    target_config_topics = []
                                    if "/" in msg.topic:
                                        base_prefix = msg.topic.rsplit('/', 1)[0]
                                        target_config_topics.append(f"{base_prefix}/config")
                                    if hasattr(settings, 'MQTT_TOPIC_SUB') and settings.MQTT_TOPIC_SUB:
                                        if settings.MQTT_TOPIC_SUB not in target_config_topics:
                                            target_config_topics.append(settings.MQTT_TOPIC_SUB)
                                    
                                    for cfg_topic in target_config_topics:
                                        client.publish(cfg_topic, relay_cmd, qos=0)
                                        self.stdout.write(self.style.SUCCESS(f"[MQTT Action] Published to {cfg_topic}: {relay_cmd}"))
                                    
                                    trigger_pir_cctv_snapshot(self.stdout)
                                else:
                                    self.stdout.write(f"[ALARM SIRINE] Sirine masih aktif/cooldown (s={normalized_s}, relay_active={self.relay_active})")
                            else:
                                self.stdout.write(f"[PIR Normal] Kondisi PIR normal (s={normalized_s})")
                                if has_detection:
                                    self.stdout.write("[PIR] Motion detected! Triggering CCTV snapshot...")
                                    trigger_pir_cctv_snapshot(self.stdout)
                                
                    # 4. Speaker status -> nms/esp32-speaker-003734fe8ce0/speaker/speaker
                    elif "/speaker/speaker" in msg.topic:
                        playing = payload.get("playing")
                        track = payload.get("track")
                        volume = payload.get("volume")
                        self.stdout.write(f"Speaker State: playing={playing}, track={track}, volume={volume}")

                    # 5. Relay rotary status -> nms/.../whitebox/relay_rotary
                    elif msg.topic.endswith("/relay_rotary"):
                        state = payload.get("state")
                        if state is not None:
                            self.relay_active = bool(state)
                            source = payload.get("source", "unknown")
                            self.stdout.write(f"[Relay Status] Rotary beacon: {'ON' if self.relay_active else 'OFF'} (source: {source})")

                except json.JSONDecodeError:
                    self.stdout.write(f"[MQTT] JSON Decode Error on payload: {payload_str}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[MQTT] Error: {e}"))

        client_id = f"django_subscriber_{os.getpid()}_{int(time.time())}"
        client = mqtt.Client(client_id)
        if USER and PASSWORD:
            client.username_pw_set(USER, PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message

        def on_disconnect(client, userdata, rc):
            if rc != 0:
                self.stdout.write(self.style.WARNING(f"[MQTT] Disconnected unexpectedly (rc={rc}). Reconnecting..."))
        client.on_disconnect = on_disconnect

        try:
            self.stdout.write(f"Connecting to Broker: {BROKER}:{PORT}")
            client.connect(BROKER, PORT, 60)
            client.loop_start()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error (Broker): {e}"))

        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopping listener..."))
            client.loop_stop()
