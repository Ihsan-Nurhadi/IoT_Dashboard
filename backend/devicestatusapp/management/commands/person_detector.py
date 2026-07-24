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

    def log_message(self, text, style_fn=None, level="info"):
        # Format text
        formatted_text = f"[{self.camera_id}] {text}"
        
        # Write to console
        if style_fn:
            self.stdout.write(style_fn(formatted_text))
        else:
            self.stdout.write(formatted_text)
        
        # Write to file
        log_file = os.path.join(settings.BASE_DIR, "person_detector.log")
        try:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a") as f:
                f.write(f"{timestamp} [{self.camera_id}] [{level.upper()}] {text}\n")
        except Exception:
            pass

    def run(self):
        self.log_message(f"Initializing YOLO model for {self.camera_id}...", self.style.WARNING)
        try:
            from ultralytics import YOLO
            # Load yolov8n model locally for this thread
            model = YOLO("yolov8n.pt")
            self.log_message(f"YOLO model loaded successfully for {self.camera_id}", self.style.SUCCESS)
        except Exception as e:
            self.log_message(f"Failed to load YOLO: {e}", self.style.ERROR)
            return

        # Ensure output directory exists
        output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
        os.makedirs(output_dir, exist_ok=True)

        self.run_onvif_loop(model, output_dir)

    def init_onvif(self):
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

        self.log_message(f"Connecting to ONVIF on {self.onvif_ip}:{self.onvif_port}...")
        
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
        except Exception:
            fixed_sub_addr = f"http://{self.onvif_ip}:{self.onvif_port}/onvif/service"
        
        # Set xaddr for PullPointSubscription in mycam.xaddrs
        mycam.xaddrs['http://www.onvif.org/ver10/events/wsdl/PullPointSubscription'] = fixed_sub_addr

        # Create pullpoint service client using ONVIFCamera's native method
        pullpoint = mycam.create_pullpoint_service()
        if hasattr(pullpoint, 'ws_client') and hasattr(pullpoint.ws_client, 'service'):
            pullpoint.ws_client.service._binding_options['address'] = fixed_sub_addr
            
        return pullpoint

    def check_for_motion(self, n):
        try:
            topic = ""
            if hasattr(n, 'Topic') and n.Topic:
                if hasattr(n.Topic, '_value_1'):
                    topic = str(n.Topic._value_1)
                else:
                    topic = str(n.Topic)

            # Check if it is an event/motion related topic
            topic_lower = topic.lower()
            topic_triggers = ["motion", "alarm", "people", "tamper", "linecross", "detector"]
            if not any(t in topic_lower for t in topic_triggers):
                return False

            self.log_message(f"Processing event topic '{topic}'. Notification data: {n}")

            # Extract message details
            if hasattr(n, 'Message') and n.Message:
                message = n.Message
                
                # Check for raw XML Element (often returned as {'_value_1': Element} in zeep)
                element = None
                if isinstance(message, dict):
                    element = message.get('_value_1')
                elif hasattr(message, '_value_1'):
                    element = message._value_1
                
                if element is not None and hasattr(element, 'iter'):
                    self.log_message(f"XML Element root tag: {element.tag}")
                    for item in element.iter():
                        self.log_message(f"  Tag: {item.tag}, Attrib: {item.attrib}")
                        if item.tag.endswith('SimpleItem'):
                            name = item.attrib.get('Name') or item.attrib.get('name', '')
                            val = item.attrib.get('Value') or item.attrib.get('value', '')
                            self.log_message(f"Parsed XML SimpleItem - Name: '{name}', Value: '{val}'")
                            if name in ["State", "IsMotion", "IsPeople", "IsLineCross", "IsTamper", "Active"] and str(val).lower() in ["true", "1"]:
                                return True
                else:
                    # Fallback to Python object attribute parsing
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
                            self.log_message(f"Parsed Obj SimpleItem - Name: '{name}', Value: '{val}' (type: {type(val)})")
                            if name in ["State", "IsMotion", "IsPeople", "IsLineCross", "IsTamper", "Active"] and str(val).lower() in ["true", "1"]:
                                return True
        except Exception as e:
            self.log_message(f"Error in check_for_motion: {e}", level="error")
        return False

    def run_onvif_loop(self, model, output_dir):
        self.log_message("Running in EVENT-DRIVEN ONVIF mode...", self.style.SUCCESS)
        
        pullpoint = None
        consecutive_failures = 0
        
        while self.running:
            if pullpoint is None:
                try:
                    pullpoint = self.init_onvif()
                    self.log_message(f"ONVIF PullPoint active on port {self.onvif_port}!", self.style.SUCCESS)
                    consecutive_failures = 0
                except Exception as onvif_err:
                    self.log_message(f"ONVIF subscription attempt failed ({onvif_err}).", self.style.ERROR)
                    pullpoint = None
                    consecutive_failures += 1
                    
                    if consecutive_failures >= 3:
                        self.log_message("ONVIF connection repeatedly failed. Waiting 30s before retrying ONVIF connection...", self.style.WARNING)
                        time.sleep(30)
                        consecutive_failures = 0
                        continue
                    
                    time.sleep(5)
                    continue

            try:
                # Poll message with 5s timeout
                msgs = pullpoint.PullMessages({'Timeout': 'PT5S', 'MessageLimit': 10})
                notifications = getattr(msgs, "NotificationMessage", None)
                
                if notifications:
                    if not isinstance(notifications, list):
                        notifications = [notifications]
                        
                    motion_detected = False
                    for n in notifications:
                        topic = getattr(n, 'Topic', None)
                        topic_val = getattr(topic, '_value_1', None) or str(topic)
                        self.log_message(f"Notification received (Topic: {topic_val})")
                        if self.check_for_motion(n):
                            motion_detected = True
                            
                    if motion_detected:
                        self.log_message("ONVIF Motion detected! Analyzing via YOLO...", self.style.WARNING)
                        self.trigger_yolo_check(model, output_dir)
                        
            except Exception as e:
                self.log_message(f"ONVIF Event Loop Error: {e}", self.style.ERROR)
                pullpoint = None  # Reset pullpoint to trigger reconnection
                time.sleep(3)

    def record_video_async(self, timestamp):
        def run_ffmpeg():
            try:
                import subprocess
                import imageio_ffmpeg
                
                output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "videos")
                os.makedirs(output_dir, exist_ok=True)
                
                filename = f"{self.camera_id}_auto_{timestamp}.mp4"
                filepath = os.path.join(output_dir, filename)
                
                self.log_message(f"Starting async video capture to {filename}...")
                
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                
                cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-rtsp_transport", "tcp",
                    "-fflags", "+genpts",
                    "-t", "10",
                    "-i", self.rtsp_url,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    filepath
                ]
                
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
                self.log_message(f"Async video capture finished and saved: {filename}", self.style.SUCCESS)
            except Exception as e:
                self.log_message(f"Error in async video capture: {e}", self.style.ERROR)

        threading.Thread(target=run_ffmpeg, daemon=True).start()

    def trigger_yolo_check(self, model, output_dir):
        cap = None
        try:
            self.log_message("Starting YOLO trigger check (checking frames over 2.5s)...")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(self.rtsp_url)
            if not cap.isOpened():
                self.log_message("Failed to open RTSP stream for trigger.", self.style.ERROR)
                return

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # We will check multiple times over a 2.5-second window
            check_interval = 0.5  # seconds
            num_checks = 5
            
            for check_idx in range(num_checks):
                # Flush buffer
                for _ in range(15):
                    cap.grab()
                ret, frame = cap.retrieve()
                if not ret or frame is None:
                    self.log_message(f"Failed to retrieve frame at check {check_idx+1}/{num_checks}", self.style.ERROR)
                    time.sleep(check_interval)
                    continue

                # Run person detection with confidence >= 0.35
                results = model(frame, classes=[0], conf=0.35, verbose=False)
                
                detected_person = False
                boxes = []
                for r in results:
                    for box in r.boxes:
                        detected_person = True
                        x1, y1, x2, y2 = box.xyxy[0]
                        conf = float(box.conf[0])
                        boxes.append((int(x1), int(y1), int(x2), int(y2), conf))

                if detected_person:
                    self.log_message(f"YOLO confirmed PERSON at check {check_idx+1}/{num_checks} (conf >= 0.35)", self.style.SUCCESS)
                    
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
                        now = timezone.localtime(timezone.now())
                        timestamp = now.strftime('%Y%m%d_%H%M%S')
                        filename = f"{self.camera_id}_auto_{timestamp}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        os.makedirs(output_dir, exist_ok=True)  # Re-create if manually deleted in runtime
                        cv2.imwrite(filepath, frame)

                        self.log_message(f"Screenshot saved: {filename}", self.style.SUCCESS)
                        
                        # Start video recording
                        self.record_video_async(timestamp)
                    else:
                        self.log_message("Person detected but cooldown active. Skipping screenshot and video recording.")
                    
                    return  # Stop checking since we already found a person

                time.sleep(check_interval)

            self.log_message("YOLO check complete: No person detected in any checked frame.")
        except Exception as err:
            self.log_message(f"trigger_yolo_check error: {err}", self.style.ERROR)
        finally:
            if cap is not None:
                cap.release()

    def run_polling_loop(self, model, output_dir):
        self.log_message("Running in 1.5s POLLING mode...", self.style.SUCCESS)
        
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

                        now = timezone.localtime(timezone.now())
                        filename = f"{self.camera_id}_auto_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, frame)

                        self.log_message(f"Person detected! Saved auto-screenshot: {filename}", self.style.SUCCESS)
            except Exception as e:
                self.log_message(f"Polling error: {e}", self.style.ERROR)

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