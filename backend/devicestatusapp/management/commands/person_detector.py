import os
import time
import cv2
import threading
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

class CameraMonitorThread(threading.Thread):
    def __init__(self, camera_id, rtsp_url, onvif_ip, onvif_port, onvif_user, onvif_password, stdout, style):
        super().__init__()
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.onvif_ip = onvif_ip
        self.onvif_port = onvif_port
        self.onvif_user = onvif_user
        self.onvif_password = onvif_password
        self.stdout = stdout
        self.style = style
        self.running = True
        self.last_capture_time = 0.0
        self.cooldown = 30.0  # 30 seconds cooldown between auto-screenshots

    def run(self):
        self.stdout.write(self.style.WARNING(f"Initializing YOLO model for {self.camera_id}..."))
        try:
            from ultralytics import YOLO
            # Load yolov8n model locally for this thread
            model = YOLO("yolov8n.pt")
            self.stdout.write(self.style.SUCCESS(f"YOLO model loaded successfully for {self.camera_id}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[{self.camera_id}] Failed to load YOLO: {e}"))
            return

        # Ensure output directory exists
        output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
        os.makedirs(output_dir, exist_ok=True)

        # Attempt ONVIF event subscription
        onvif_active = False
        pullpoint = None
        
        try:
            from onvif import ONVIFCamera
            from urllib.parse import urlparse
            
            def rewrite_url_to_target(url_str, target_ip, target_port):
                if not url_str:
                    return url_str
                try:
                    parsed = urlparse(str(url_str))
                    path_and_query = parsed.path
                    if parsed.query:
                        path_and_query += f"?{parsed.query}"
                    return f"http://{target_ip}:{target_port}{path_and_query}"
                except Exception:
                    return url_str

            self.stdout.write(f"[{self.camera_id}] Connecting to ONVIF on {self.onvif_ip}:{self.onvif_port}...")
            
            # WSDL dir path
            wsdl_dir = os.path.join(settings.BASE_DIR, "wsdl")
            
            mycam = ONVIFCamera(
                self.onvif_ip, 
                self.onvif_port, 
                self.onvif_user, 
                self.onvif_password, 
                wsdl_dir=wsdl_dir
            )
            
            # Rewrite all service XAddrs returned by camera to match external NAT/tunnel IP & port
            for ns, addr in list(mycam.xaddrs.items()):
                if addr:
                    mycam.xaddrs[ns] = rewrite_url_to_target(addr, self.onvif_ip, self.onvif_port)
            
            # Create Event Service
            event_service = mycam.create_events_service()
            if hasattr(event_service, 'ws_client') and hasattr(event_service.ws_client, 'service'):
                cur_addr = getattr(event_service.ws_client.service, '_binding_options', {}).get('address')
                if cur_addr:
                    event_service.ws_client.service._binding_options['address'] = rewrite_url_to_target(cur_addr, self.onvif_ip, self.onvif_port)
            
            # Create PullPoint subscription
            subscription_ref = event_service.CreatePullPointSubscription()
            try:
                sub_addr = subscription_ref.SubscriptionReference.Address._value_1
                fixed_sub_addr = rewrite_url_to_target(sub_addr, self.onvif_ip, self.onvif_port)
                subscription_ref.SubscriptionReference.Address._value_1 = fixed_sub_addr
            except Exception:
                pass
            
            # Initialize PullPoint service with rewritten subscription reference
            pullpoint = mycam.pullpoint(subscription_ref)
            if hasattr(pullpoint, 'ws_client') and hasattr(pullpoint.ws_client, 'service'):
                cur_addr = getattr(pullpoint.ws_client.service, '_binding_options', {}).get('address')
                if cur_addr:
                    pullpoint.ws_client.service._binding_options['address'] = rewrite_url_to_target(cur_addr, self.onvif_ip, self.onvif_port)
            
            onvif_active = True
            
            self.stdout.write(self.style.SUCCESS(
                f"[{self.camera_id}] ONVIF PullPoint active on port {self.onvif_port}!"
            ))
        except Exception as onvif_err:
            self.stdout.write(self.style.ERROR(
                f"[{self.camera_id}] ONVIF init failed ({onvif_err}). Falling back to 1.5s POLLING mode..."
            ))

        if onvif_active and pullpoint:
            self.run_onvif_loop(model, pullpoint, output_dir)
        else:
            self.run_polling_loop(model, output_dir)

    def check_for_motion(self, n):
        try:
            topic = ""
            if hasattr(n, 'Topic') and n.Topic:
                if hasattr(n.Topic, '_value_1'):
                    topic = str(n.Topic._value_1)
                else:
                    topic = str(n.Topic)

            # Check if it is a motion related event topic
            if "Motion" not in topic and "MotionAlarm" not in topic:
                return False

            # Extract message details
            if hasattr(n, 'Message') and n.Message:
                message = n.Message
                if hasattr(message, 'Data') and message.Data:
                    data = message.Data
                    items = []
                    if hasattr(data, 'SimpleItem'):
                        items = data.SimpleItem
                        if not isinstance(items, list):
                            items = [items]
                    
                    for item in items:
                        name = getattr(item, '_attr_Name', '') or getattr(item, 'Name', '')
                        val = getattr(item, '_attr_Value', '') or getattr(item, 'Value', '')
                        if name == "State" and str(val).lower() in ["true", "1"]:
                            return True
        except Exception:
            pass
        return False

    def run_onvif_loop(self, model, pullpoint, output_dir):
        self.stdout.write(self.style.SUCCESS(f"[{self.camera_id}] Running in EVENT-DRIVEN ONVIF mode..."))
        
        while self.running:
            try:
                # Poll message with 5s timeout
                msgs = pullpoint.PullMessages(Timeout="PT5S", MessageLimit=10)
                notifications = getattr(msgs, "NotificationMessage", None)
                
                if notifications:
                    if not isinstance(notifications, list):
                        notifications = [notifications]
                        
                    motion_detected = False
                    for n in notifications:
                        if self.check_for_motion(n):
                            motion_detected = True
                            break
                            
                    if motion_detected:
                        self.stdout.write(self.style.WARNING(
                            f"[{self.camera_id}] ONVIF Motion detected! Analyzing via YOLO..."
                        ))
                        self.trigger_yolo_check(model, output_dir)
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{self.camera_id}] ONVIF Event Loop Error: {e}"))
                time.sleep(2)

    def trigger_yolo_check(self, model, output_dir):
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(self.rtsp_url)
            if not cap.isOpened():
                self.stdout.write(self.style.ERROR(f"[{self.camera_id}] Failed to open RTSP stream for trigger."))
                return

            for _ in range(5):
                cap.grab()
            ret, frame = cap.retrieve()
            cap.release()

            if not ret:
                self.stdout.write(self.style.ERROR(f"[{self.camera_id}] Failed to retrieve frame for trigger."))
                return

            # Run person detection
            results = model(frame, classes=[0], conf=0.5, verbose=False)
            
            detected_person = False
            boxes = []
            for r in results:
                for box in r.boxes:
                    detected_person = True
                    x1, y1, x2, y2 = box.xyxy[0]
                    conf = float(box.conf[0])
                    boxes.append((int(x1), int(y1), int(x2), int(y2), conf))

            if detected_person:
                now_time = time.time()
                if now_time - self.last_capture_time >= self.cooldown:
                    self.last_capture_time = now_time

                    # Draw bounding boxes
                    for (x1, y1, x2, y2, conf) in boxes:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"Person {conf:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # Save proof
                    now = timezone.now()
                    filename = f"{self.camera_id}_auto_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(output_dir, filename)
                    cv2.imwrite(filepath, frame)

                    self.stdout.write(self.style.SUCCESS(
                        f"[{self.camera_id}] YOLO confirmed PERSON. Screenshot saved: {filename}"
                    ))
                else:
                    self.stdout.write(f"[{self.camera_id}] Person detected but cooldown active. Skipping screenshot.")
            else:
                self.stdout.write(f"[{self.camera_id}] ONVIF Motion event was not a person. Discarded frame.")
        except Exception as err:
            self.stdout.write(self.style.ERROR(f"[{self.camera_id}] trigger_yolo_check error: {err}"))

    def run_polling_loop(self, model, output_dir):
        self.stdout.write(self.style.SUCCESS(f"[{self.camera_id}] Running in 1.5s POLLING mode..."))
        
        while self.running:
            try:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                cap = cv2.VideoCapture(self.rtsp_url)
                if not cap.isOpened():
                    time.sleep(5)
                    continue

                for _ in range(5):
                    cap.grab()
                ret, frame = cap.retrieve()
                cap.release()

                if not ret:
                    time.sleep(2)
                    continue

                results = model(frame, classes=[0], conf=0.5, verbose=False)
                
                detected_person = False
                boxes = []
                for r in results:
                    for box in r.boxes:
                        detected_person = True
                        x1, y1, x2, y2 = box.xyxy[0]
                        conf = float(box.conf[0])
                        boxes.append((int(x1), int(y1), int(x2), int(y2), conf))

                if detected_person:
                    now_time = time.time()
                    if now_time - self.last_capture_time >= self.cooldown:
                        self.last_capture_time = now_time

                        for (x1, y1, x2, y2, conf) in boxes:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            label = f"Person {conf:.2f}"
                            cv2.putText(frame, label, (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        now = timezone.now()
                        filename = f"{self.camera_id}_auto_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, frame)

                        self.stdout.write(self.style.SUCCESS(
                            f"[{self.camera_id}] Person detected! Saved auto-screenshot: {filename}"
                        ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{self.camera_id}] Polling error: {e}"))

            time.sleep(1.5)

    def stop(self):
        self.running = False


class Command(BaseCommand):
    help = 'Runs background YOLO person detection on CCTV feeds triggered by ONVIF motion events.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting CCTV Person Detection Monitor Service (ONVIF Triggered)..."))

        # CCTV 1 Config
        cctv1_rtsp = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"
        cctv1_onvif_ip = "10.10.0.5"
        cctv1_onvif_port = 2020  # Change if port-forwarded differently
        cctv1_user = "nykws1"
        cctv1_pass = "nykworkshop"

        # CCTV 2 Config
        cctv2_rtsp = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"
        cctv2_onvif_ip = "10.10.0.5"
        cctv2_onvif_port = 2021  # Change if port-forwarded differently (e.g. 2021)
        cctv2_user = "nykws2"
        cctv2_pass = "nykworkshop"

        t1 = CameraMonitorThread(
            camera_id="cctv",
            rtsp_url=cctv1_rtsp,
            onvif_ip=cctv1_onvif_ip,
            onvif_port=cctv1_onvif_port,
            onvif_user=cctv1_user,
            onvif_password=cctv1_pass,
            stdout=self.stdout,
            style=self.style
        )
        
        t2 = CameraMonitorThread(
            camera_id="cctv2",
            rtsp_url=cctv2_rtsp,
            onvif_ip=cctv2_onvif_ip,
            onvif_port=cctv2_onvif_port,
            onvif_user=cctv2_user,
            onvif_password=cctv2_pass,
            stdout=self.stdout,
            style=self.style
        )

        t1.start()
        t2.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopping monitors..."))
            t1.stop()
            t2.stop()
            t1.join()
            t2.join()
            self.stdout.write(self.style.SUCCESS("Monitors stopped successfully."))