import os
import time
import cv2
import threading
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

class CameraMonitorThread(threading.Thread):
    def __init__(self, camera_id, rtsp_url, stdout, style):
        super().__init__()
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
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

        self.stdout.write(self.style.SUCCESS(f"Auto person detector running for {self.camera_id}..."))

        while self.running:
            try:
                # Set TCP transport option for OpenCV ffmpeg backend
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                cap = cv2.VideoCapture(self.rtsp_url)
                if not cap.isOpened():
                    self.stdout.write(f"[{self.camera_id}] Error opening stream. Retrying in 5s...")
                    time.sleep(5)
                    continue

                # Skip a few initial frames to clear the decoder stream buffer
                for _ in range(5):
                    cap.grab()
                ret, frame = cap.retrieve()
                cap.release()

                if not ret:
                    self.stdout.write(f"[{self.camera_id}] Failed to retrieve frame. Retrying in 2s...")
                    time.sleep(2)
                    continue

                # Run person class detection (class 0, conf threshold 0.5)
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

                        # Draw bounding boxes and labels
                        for (x1, y1, x2, y2, conf) in boxes:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            label = f"Person {conf:.2f}"
                            cv2.putText(frame, label, (x1, y1 - 10), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        # Write screenshot to disk
                        now = timezone.now()
                        filename = f"{self.camera_id}_auto_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        cv2.imwrite(filepath, frame)

                        self.stdout.write(self.style.SUCCESS(
                            f"[{self.camera_id}] Person detected! Saved auto-screenshot: {filename}"
                        ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[{self.camera_id}] Monitoring error: {e}"))

            # Processing query interval (check camera every 1.5 seconds)
            time.sleep(1.5)

    def stop(self):
        self.running = False


class Command(BaseCommand):
    help = 'Runs background YOLO person detection on CCTV feeds and saves screenshots automatically.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting CCTV Person Detection Monitor Service..."))

        # Setup monitoring threads for both camera channels
        cctv1_url = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"
        cctv2_url = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"

        t1 = CameraMonitorThread("cctv", cctv1_url, self.stdout, self.style)
        t2 = CameraMonitorThread("cctv2", cctv2_url, self.stdout, self.style)

        t1.start()
        t2.start()

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nStopping monitors..."))
            t1.stop()
            t2.stop()
            t1.join()
            t2.join()
            self.stdout.write(self.style.SUCCESS("Monitors stopped successfully."))