import os
import time
import cv2
import threading
import concurrent.futures
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
        self.daemon = True   # Thread dies with main process

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
        """
        Outer restart loop: if run_onvif_loop() crashes for any reason,
        this will wait 30s and restart everything (including YOLO model reload).
        This ensures the thread NEVER dies permanently.
        """
        while self.running:
            try:
                self.log_message(f"Initializing YOLO model for {self.camera_id}...", self.style.WARNING)
                try:
                    from ultralytics import YOLO
                    # Load yolov8n model locally for this thread
                    model = YOLO("yolov8n.pt")
                    self.log_message(f"YOLO model loaded successfully for {self.camera_id}", self.style.SUCCESS)
                except Exception as e:
                    self.log_message(f"Failed to load YOLO: {e}. Retrying in 30s...", self.style.ERROR, level="error")
                    time.sleep(30)
                    continue

                # Ensure output directory exists
                output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
                os.makedirs(output_dir, exist_ok=True)

                self.run_onvif_loop(model, output_dir)

            except Exception as e:
                self.log_message(
                    f"FATAL: Unhandled exception in main run loop: {e}. Restarting in 30s...",
                    self.style.ERROR,
                    level="error"
                )
                time.sleep(30)

        self.log_message("Thread stopped (running=False).", level="info")

    def stop(self):
        self.running = False


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
        
        # Create PullPoint subscription with 1-hour TTL.
        # Without this, Tapo cameras expire the subscription in ~1-5 minutes
        # and PullMessages() silently returns empty forever (no exception raised).
        try:
            subscription_ref = event_service.CreatePullPointSubscription({
                'InitialTerminationTime': 'PT1H'
            })
        except Exception:
            # Fallback: some firmware ignores the param — create without it
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

        # Record when this subscription was created (used for proactive renewal)
        subscription_start_time = time.time()
        self.log_message(
            f"ONVIF subscription created with PT1H TTL at {timezone.now().strftime('%H:%M:%S')}",
            self.style.SUCCESS
        )

        return pullpoint, subscription_start_time


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
                return False, False

            self.log_message(f"Processing event topic '{topic}'. Notification data: {n}")

            is_motion = False
            is_people = "people" in topic_lower

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
                                is_motion = True
                                if name == "IsPeople":
                                    is_people = True
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
                                is_motion = True
                                if name == "IsPeople":
                                    is_people = True

            return is_motion, is_people
        except Exception as e:
            self.log_message(f"Error in check_for_motion: {e}", level="error")
        return False, False

    def _pull_messages_with_timeout(self, pullpoint, timeout_seconds=15):
        """
        Wrap PullMessages in a thread with timeout to prevent it hanging forever.
        Returns None if timeout is exceeded — the caller should reconnect.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                pullpoint.PullMessages,
                {'Timeout': 'PT5S', 'MessageLimit': 10}
            )
            try:
                return future.result(timeout=timeout_seconds)
            except concurrent.futures.TimeoutError:
                return None
            except Exception:
                raise  # Re-raise other exceptions to caller

    def verify_antennas_integrity(self):
        import cv2
        import os
        import json
        from devicestatusapp.models import CCTVCamera
        
        try:
            cam = CCTVCamera.objects.filter(camera_id=self.camera_id, is_active=True).first()
        except Exception as e:
            self.log_message(f"[Visual Check] Database error loading camera: {e}")
            return
            
        if not cam:
            return
            
        try:
            zones = json.loads(cam.detection_zones or '[]')
        except Exception:
            return
            
        if not zones:
            return
            
        # Check if baselines exist for any of the zones (standard or time-of-day specific)
        import glob
        baselines_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
        zones_to_check = []
        for zone in zones:
            name = zone.get('name', '').strip().replace(' ', '_')
            if not name:
                continue
            pattern = os.path.join(baselines_dir, f"baseline_{self.camera_id}_{name}*.jpg")
            matching_paths = glob.glob(pattern)
            if matching_paths:
                zones_to_check.append((zone, name, matching_paths))
                
        if not zones_to_check:
            return
            
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.log_message("[Visual Check] Failed to open RTSP stream.")
            return
            
        for _ in range(5):
            cap.grab()
        ret, frame = cap.retrieve()
        cap.release()
        
        if not ret or frame is None:
            self.log_message("[Visual Check] Failed to retrieve frame.")
            return
            
        height, width = frame.shape[:2]
        
        for zone, name, baseline_paths in zones_to_check:
            points = zone.get('points', [])
            if len(points) < 3:
                continue
                
            x_coords = [float(p[0]) for p in points]
            y_coords = [float(p[1]) for p in points]
            
            xmin_ratio, xmax_ratio = min(x_coords), max(x_coords)
            ymin_ratio, ymax_ratio = min(y_coords), max(y_coords)
            
            xmin = int(xmin_ratio * width)
            xmax = int(xmax_ratio * width)
            ymin = int(ymin_ratio * height)
            ymax = int(ymax_ratio * height)
            
            w_px = xmax - xmin
            h_px = ymax - ymin
            
            pad_x = max(25, int(w_px * 0.15))
            pad_y = max(25, int(h_px * 0.15))
            
            s_xmin = max(0, xmin - pad_x)
            s_xmax = min(width, xmax + pad_x)
            s_ymin = max(0, ymin - pad_y)
            s_ymax = min(height, ymax + pad_y)
            
            search_region = frame[s_ymin:s_ymax, s_xmin:s_xmax]
            sr_h, sr_w = search_region.shape[:2]
            
            best_score = -1.0
            
            for b_path in baseline_paths:
                baseline_img = cv2.imread(b_path)
                if baseline_img is None:
                    continue
                tb_h, tb_w = baseline_img.shape[:2]
                if tb_h < 5 or tb_w < 5:
                    continue
                    
                local_search = search_region.copy()
                local_sr_h, local_sr_w = sr_h, sr_w
                
                if tb_h > local_sr_h or tb_w > local_sr_w:
                    target_w = max(5, xmax - xmin)
                    target_h = max(5, ymax - ymin)
                    baseline_img = cv2.resize(baseline_img, (target_w, target_h))
                    tb_h, tb_w = baseline_img.shape[:2]
                    
                if local_sr_h < tb_h or local_sr_w < tb_w:
                    local_search = frame[ymin:ymax, xmin:xmax]
                    local_sr_h, local_sr_w = local_search.shape[:2]
                    if local_sr_h < tb_h or local_sr_w < tb_w:
                        continue
                        
                try:
                    res = cv2.matchTemplate(local_search, baseline_img, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val > best_score:
                        best_score = max_val
                except Exception as match_err:
                    self.log_message(f"[Visual Check] Match template error for {name} on {os.path.basename(b_path)}: {match_err}")
                    continue
            
            # Lower the similarity threshold to 0.55 to make it highly robust against compression artifacts,
            # night transition noise, wind vibrations, heat haze, and sky color backdrop fluctuations.
            threshold = 0.55
            self.log_message(f"[Visual Check] Zone '{name}': Max match score = {best_score:.3f} (Threshold: {threshold})")
            
            if best_score < threshold:
                self.log_message(f"[Visual Check] ALARM! Zone '{name}' best similarity {best_score:.3f} is below threshold!", self.style.ERROR)
                
                cooldown_key = f"last_alarm_{name}"
                last_alarm = getattr(self, cooldown_key, 0.0)
                if time.time() - last_alarm < 300:
                    continue
                setattr(self, cooldown_key, time.time())
                
                alert_frame = frame.copy()
                
                poly_pts = []
                for pt in points:
                    poly_pts.append([int(float(pt[0]) * width), int(float(pt[1]) * height)])
                import numpy as np
                cv2.polylines(alert_frame, [np.array(poly_pts, dtype=np.int32)], isClosed=True, color=(0, 0, 255), thickness=3)
                
                label_y = ymin - 15 if ymin - 15 > 20 else ymin + 25
                cv2.putText(
                    alert_frame, 
                    f"STOLEN ALERT: {name} (Match: {best_score*100:.1f}%)", 
                    (xmin, label_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 0, 255), 
                    2
                )
                
                photos_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
                os.makedirs(photos_dir, exist_ok=True)
                timestamp_str = timezone.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.camera_id}_stolen_{name}_{timestamp_str}.jpg"
                filepath = os.path.join(photos_dir, filename)
                cv2.imwrite(filepath, alert_frame)
                
                self.log_message(f"[Visual Check] Saved alert photo: {filename}", self.style.SUCCESS)

    def run_onvif_loop(self, model, output_dir):
        self.log_message("Running in EVENT-DRIVEN ONVIF mode...", self.style.SUCCESS)

        pullpoint = None
        subscription_start_time = None
        consecutive_failures = 0

        # ── Tuneable constants ───────────────────────────────────────────────
        # After this many seconds, proactively recreate the subscription
        # (prevents silent expiry; Tapo default TTL is often 1–5 min without PT1H).
        SUBSCRIPTION_MAX_AGE_SEC = 50 * 60  # 50 minutes

        # If this many consecutive PullMessages return empty, assume the
        # subscription silently expired and force a reconnect.
        # Each PullMessages call holds up to ~5s, so 120 × 5s ≈ 10 min of silence.
        EMPTY_POLL_RECONNECT_THRESHOLD = 120

        # Heartbeat log interval
        HEARTBEAT_INTERVAL_SEC = 5 * 60  # every 5 minutes

        consecutive_empty_polls = 0
        last_heartbeat_time = time.time()

        while self.running:

            # ── Antenna Visual Integrity Check ──────────────────────────────
            now_time = time.time()
            if not hasattr(self, 'last_antenna_check_time') or now_time - self.last_antenna_check_time >= 60:
                self.last_antenna_check_time = now_time
                try:
                    self.verify_antennas_integrity()
                except Exception as ve:
                    self.log_message(f"Error in verify_antennas_integrity: {ve}", self.style.ERROR)

            # ── Heartbeat ──────────────────────────────────────────────────
            now = time.time()
            if now - last_heartbeat_time >= HEARTBEAT_INTERVAL_SEC:
                sub_age_min = ((now - subscription_start_time) / 60) if subscription_start_time else 0
                self.log_message(
                    f"[HEARTBEAT] ONVIF loop alive. "
                    f"Subscription age: {sub_age_min:.1f}min. "
                    f"Consecutive empty polls: {consecutive_empty_polls}.",
                    level="info"
                )
                last_heartbeat_time = now

            # ── Proactive subscription renewal ─────────────────────────────
            if pullpoint is not None and subscription_start_time is not None:
                sub_age = time.time() - subscription_start_time
                if sub_age >= SUBSCRIPTION_MAX_AGE_SEC:
                    self.log_message(
                        f"[RENEW] Subscription age {sub_age/60:.1f}min reached limit. "
                        f"Proactively recreating subscription...",
                        self.style.WARNING,
                        level="warning"
                    )
                    pullpoint = None
                    subscription_start_time = None
                    consecutive_empty_polls = 0

            # ── Silent expiry detection ────────────────────────────────────
            if pullpoint is not None and consecutive_empty_polls >= EMPTY_POLL_RECONNECT_THRESHOLD:
                self.log_message(
                    f"[SILENT EXPIRY] {consecutive_empty_polls} consecutive empty polls "
                    f"(~{consecutive_empty_polls * 5 / 60:.1f}min of silence). "
                    f"Subscription likely expired silently. Forcing reconnect...",
                    self.style.ERROR,
                    level="error"
                )
                pullpoint = None
                subscription_start_time = None
                consecutive_empty_polls = 0

            # ── Connect / Reconnect ────────────────────────────────────────
            if pullpoint is None:
                try:
                    pullpoint, subscription_start_time = self.init_onvif()
                    self.log_message(f"ONVIF PullPoint active on port {self.onvif_port}!", self.style.SUCCESS)
                    consecutive_failures = 0
                    consecutive_empty_polls = 0
                    last_heartbeat_time = time.time()
                except Exception as onvif_err:
                    self.log_message(f"ONVIF subscription attempt failed ({onvif_err}).", self.style.ERROR, level="error")
                    pullpoint = None
                    subscription_start_time = None
                    consecutive_failures += 1

                    # Exponential-ish backoff capped at 5 minutes
                    wait_sec = min(5 * consecutive_failures, 300)
                    self.log_message(
                        f"Retry #{consecutive_failures}. Waiting {wait_sec}s before next attempt...",
                        self.style.WARNING
                    )
                    time.sleep(wait_sec)
                    continue

            # ── Poll messages ──────────────────────────────────────────────
            try:
                msgs = self._pull_messages_with_timeout(pullpoint, timeout_seconds=15)

                if msgs is None:
                    # PullMessages hung and was killed by timeout
                    self.log_message(
                        "PullMessages timed out (>15s). Subscription may be stuck. Reconnecting...",
                        self.style.ERROR,
                        level="error"
                    )
                    pullpoint = None
                    subscription_start_time = None
                    consecutive_empty_polls = 0
                    time.sleep(3)
                    continue

                notifications = getattr(msgs, "NotificationMessage", None)

                if not notifications:
                    consecutive_empty_polls += 1
                else:
                    # Got notifications → reset empty poll counter
                    consecutive_empty_polls = 0

                    if not isinstance(notifications, list):
                        notifications = [notifications]

                    motion_detected = False
                    people_detected = False
                    for n in notifications:
                        topic = getattr(n, 'Topic', None)
                        topic_val = getattr(topic, '_value_1', None) or str(topic)
                        self.log_message(f"Notification received (Topic: {topic_val})")
                        is_m, is_p = self.check_for_motion(n)
                        if is_m:
                            motion_detected = True
                        if is_p:
                            people_detected = True

                    if motion_detected:
                        self.log_message(
                            f"ONVIF Motion detected (is_people={people_detected})! Analyzing via YOLO...",
                            self.style.WARNING
                        )
                        self.trigger_yolo_check(model, output_dir, onvif_is_people=people_detected)

            except Exception as e:
                self.log_message(f"ONVIF Event Loop Error: {e}", self.style.ERROR, level="error")
                pullpoint = None  # Reset pullpoint to trigger reconnection
                subscription_start_time = None
                consecutive_empty_polls = 0
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

    def trigger_yolo_check(self, model, output_dir, onvif_is_people=False):
        cap = None
        try:
            self.log_message(f"Starting YOLO trigger check (checking frames over 2.5s, onvif_is_people={onvif_is_people})...")
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(self.rtsp_url)
            if not cap.isOpened():
                self.log_message("Failed to open RTSP stream for trigger.", self.style.ERROR)
                return

            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            check_interval = 0.4  # seconds
            num_checks = 6
            
            best_frame = None
            detected_person = False
            boxes = []
            
            for check_idx in range(num_checks):
                # Flush buffer
                for _ in range(8):
                    cap.grab()
                ret, frame = cap.retrieve()
                if not ret or frame is None:
                    self.log_message(f"Failed to retrieve frame at check {check_idx+1}/{num_checks}", self.style.ERROR)
                    time.sleep(check_interval)
                    continue

                if best_frame is None:
                    best_frame = frame.copy()

                # Run person detection with conf >= 0.25 (lower threshold for night/distance)
                results = model(frame, classes=[0], conf=0.25, verbose=False)
                
                cur_boxes = []
                for r in results:
                    for box in r.boxes:
                        detected_person = True
                        x1, y1, x2, y2 = box.xyxy[0]
                        conf = float(box.conf[0])
                        cur_boxes.append((int(x1), int(y1), int(x2), int(y2), conf))

                if detected_person:
                    self.log_message(f"YOLO confirmed PERSON at check {check_idx+1}/{num_checks} (conf >= 0.25)", self.style.SUCCESS)
                    best_frame = frame
                    boxes = cur_boxes
                    break

                time.sleep(check_interval)

            now_time = time.time()
            if now_time - self.last_capture_time < self.cooldown:
                self.log_message("Cooldown active. Skipping screenshot and video recording.")
                return

            # If YOLO detected a person OR ONVIF explicitly reported IsPeople/PeopleDetector = true:
            if detected_person or onvif_is_people:
                self.last_capture_time = now_time

                save_frame = best_frame if best_frame is not None else frame

                if detected_person:
                    # Draw bounding boxes
                    for (x1, y1, x2, y2, conf) in boxes:
                        cv2.rectangle(save_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"Person {conf:.2f}"
                        cv2.putText(save_frame, label, (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    # Fallback label for ONVIF Tapo AI detection when YOLO missed bounding box due to RTSP delay/night vision
                    self.log_message("YOLO missed bounding box, but Tapo ONVIF confirmed IsPeople=true. Saving Tapo AI proof snapshot!", self.style.WARNING)
                    cv2.putText(save_frame, "Person (Tapo AI)", (20, 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # Save proof image
                now = timezone.now()
                timestamp = now.strftime('%Y%m%d_%H%M%S')
                filename = f"{self.camera_id}_auto_{timestamp}.jpg"
                filepath = os.path.join(output_dir, filename)
                os.makedirs(output_dir, exist_ok=True)
                cv2.imwrite(filepath, save_frame)

                self.log_message(f"Detection proof saved: {filename}", self.style.SUCCESS)
                
                # Start 10s video recording
                self.record_video_async(timestamp)
            else:
                self.log_message("YOLO check complete: No person detected in any checked frame.")

        except Exception as err:
            self.log_message(f"trigger_yolo_check error: {err}", self.style.ERROR, level="error")
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

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

                        now = timezone.now()
                        filename = f"{self.camera_id}_auto_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, frame)

                        self.log_message(f"Person detected! Saved auto-screenshot: {filename}", self.style.SUCCESS)
            except Exception as e:
                self.log_message(f"Polling error: {e}", self.style.ERROR)

            time.sleep(1.5)

class WatchdogThread(threading.Thread):
    """
    Monitors CameraMonitorThreads and restarts them if they die unexpectedly.
    Checks every 30 seconds. Acts as a safety net on top of the
    self-healing outer loop already built into CameraMonitorThread.run().
    """
    def __init__(self, managed_list, stdout, style):
        super().__init__()
        self.managed = managed_list  # list of {'config': {...}, 'thread': CameraMonitorThread}
        self.stdout = stdout
        self.style = style
        self.running = True
        self.daemon = True

    def _log(self, text, style_fn=None):
        msg = f"[Watchdog] {text}"
        if style_fn:
            self.stdout.write(style_fn(msg))
        else:
            self.stdout.write(msg)
        log_file = os.path.join(settings.BASE_DIR, "person_detector.log")
        try:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a") as f:
                f.write(f"{timestamp} [Watchdog] [INFO] {text}\n")
        except Exception:
            pass

    def run(self):
        self._log("Watchdog started. Monitoring camera threads every 30s.", self.style.SUCCESS)
        while self.running:
            time.sleep(30)
            if not self.running:
                break
            for m in self.managed:
                t = m['thread']
                if not t.is_alive():
                    self._log(
                        f"Thread for {m['config']['camera_id']} is DEAD. Restarting...",
                        self.style.ERROR
                    )
                    new_thread = CameraMonitorThread(
                        **m['config'],
                        stdout=self.stdout,
                        style=self.style
                    )
                    new_thread.start()
                    m['thread'] = new_thread
                    self._log(
                        f"Thread for {m['config']['camera_id']} restarted successfully.",
                        self.style.SUCCESS
                    )

    def stop_all(self):
        self.running = False
        for m in self.managed:
            m['thread'].stop()


class MediaCleanupThread(threading.Thread):
    def __init__(self, stdout, style):
        super().__init__()
        self.stdout = stdout
        self.style = style
        self.running = True
        self.daemon = True

    def run(self):
        from django.core.management import call_command
        # Wait 10s on startup before first cleanup
        time.sleep(10)
        while self.running:
            try:
                self.stdout.write(self.style.WARNING("[CleanupWorker] Running automatic background CCTV media cleanup..."))
                call_command('cleanup_media', days=7, max_size=2000, target_size=1500)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[CleanupWorker] Automatic media cleanup error: {e}"))

            # Sleep 1 hour (3600s)
            for _ in range(3600):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        self.running = False


class Command(BaseCommand):
    help = 'Runs background YOLO person detection on CCTV feeds triggered by ONVIF motion events.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting CCTV Person Detection Monitor Service (ONVIF Triggered)..."))

        from devicestatusapp.models import CCTVCamera
        import urllib.parse
        
        cameras_config = []
        try:
            db_cameras = CCTVCamera.objects.filter(is_active=True)
            for dc in db_cameras:
                onvif_ip = '10.10.0.5'
                onvif_port = 2020
                if dc.onvif_url:
                    try:
                        parsed = urllib.parse.urlparse(dc.onvif_url)
                        netloc = parsed.netloc
                        if ":" in netloc:
                            onvif_ip, port_str = netloc.split(":")
                            onvif_port = int(port_str)
                        else:
                            onvif_ip = netloc
                            onvif_port = 80
                    except Exception:
                        pass
                
                rtsp_url = dc.rtsp_url
                if dc.username and dc.password and "@" not in rtsp_url and "rtsp://" in rtsp_url:
                    rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{dc.username}:{dc.password}@")
                    
                cameras_config.append({
                    'camera_id': dc.camera_id,
                    'rtsp_url': rtsp_url,
                    'onvif_ip': onvif_ip,
                    'onvif_port': onvif_port,
                    'onvif_user': dc.username or '',
                    'onvif_password': dc.password or '',
                })
        except Exception as db_err:
            self.stdout.write(self.style.ERROR(f"Error loading cameras from DB: {db_err}"))

        if not cameras_config:
            cameras_config = [
                {
                    'camera_id': 'cctv',
                    'rtsp_url': 'rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1',
                    'onvif_ip': '10.10.0.5',
                    'onvif_port': 2020,
                    'onvif_user': 'nykws1',
                    'onvif_password': 'nykworkshop',
                },
                {
                    'camera_id': 'cctv2',
                    'rtsp_url': 'rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1',
                    'onvif_ip': '10.10.0.5',
                    'onvif_port': 2021,
                    'onvif_user': 'nykws2',
                    'onvif_password': 'nykworkshop',
                },
            ]

        # Build managed thread list and start all camera threads
        managed_list = []
        for cfg in cameras_config:
            t = CameraMonitorThread(**cfg, stdout=self.stdout, style=self.style)
            managed_list.append({'config': cfg, 'thread': t})
            t.start()
            self.stdout.write(self.style.SUCCESS(f"Started camera thread: {cfg['camera_id']}"))

        # Watchdog monitors and auto-restarts dead camera threads
        watchdog = WatchdogThread(managed_list, stdout=self.stdout, style=self.style)
        watchdog.start()

        # Media cleanup worker
        tc = MediaCleanupThread(stdout=self.stdout, style=self.style)
        tc.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopping monitors..."))
            watchdog.stop_all()
            tc.stop()
            self.stdout.write(self.style.SUCCESS("Monitors stopped successfully."))