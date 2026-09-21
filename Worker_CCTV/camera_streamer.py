import os
import time
import threading
import logging
import cv2
import numpy as np

logger = logging.getLogger("cctv_streamer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s")


class CameraStreamer:
    """
    Manages continuous RTSP stream ingestion in a background thread.
    Caches the freshest encoded JPEG frame so multiple web clients
    can stream simultaneously without multiple connections to the camera.
    """

    def __init__(
        self,
        host=None,
        port=None,
        path=None,
        user=None,
        password=None,
        rtsp_url_override=None,
        target_fps=20,
        stream_width=1280,
        stream_quality=75,
        rtsp_transport="tcp",
    ):
        self.host = host or os.getenv("CAMERA_HOST", "10.10.1.17")
        self.port = int(port or os.getenv("RTSP_PORT", 554))
        self.path = path or os.getenv("RTSP_PATH", "/stream1")
        if not self.path.startswith("/"):
            self.path = "/" + self.path

        self.user = user or os.getenv("CAMERA_USER", "NMSIOTYOGYA1")
        self.password = password or os.getenv("CAMERA_PASS", "Nayaka2025")
        self.rtsp_url_override = rtsp_url_override or os.getenv("RTSP_URL")

        self.target_fps = int(target_fps or os.getenv("TARGET_FPS", 15))
        self.stream_width = int(stream_width or os.getenv("STREAM_WIDTH", 854))
        self.stream_quality = int(stream_quality or os.getenv("STREAM_QUALITY", 60))
        self.rtsp_transport = rtsp_transport or os.getenv("RTSP_TRANSPORT", "tcp")

        # Runtime state
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.viewer_lock = threading.Lock()
        self.active_viewers = 0
        self.stop_timer = None

        self.latest_jpeg = None
        self.latest_frame = None
        self.latest_frame_time = 0
        self.connected = False
        self.resolution = "Unknown"
        self.measured_fps = 0.0
        self.total_frames = 0
        self.reconnect_count = 0
        self.last_error = None

    def add_viewer(self):
        with self.viewer_lock:
            if self.stop_timer:
                self.stop_timer.cancel()
                self.stop_timer = None
            self.active_viewers += 1
            if not self.running:
                logger.info(f"Viewer connected (total: {self.active_viewers}). Starting on-demand RTSP capture...")
                self.start()

    def remove_viewer(self):
        with self.viewer_lock:
            self.active_viewers = max(0, self.active_viewers - 1)
            logger.info(f"Viewer disconnected (remaining: {self.active_viewers})")
            if self.active_viewers == 0:
                if self.stop_timer:
                    self.stop_timer.cancel()
                self.stop_timer = threading.Timer(4.0, self._delayed_stop)
                self.stop_timer.daemon = True
                self.stop_timer.start()

    def _delayed_stop(self):
        with self.viewer_lock:
            if self.active_viewers == 0 and self.running:
                logger.info("No active viewers for 4s. Stopping RTSP stream to prevent lag buffer and save bandwidth.")
                self.stop()

    def get_rtsp_url(self, mask_password=False):
        if self.rtsp_url_override:
            url = self.rtsp_url_override
            if mask_password and "@" in url:
                parts = url.split("@")
                proto_user = parts[0].split(":")
                return f"{proto_user[0]}:***@{parts[1]}"
            return url

        if self.user and self.password:
            pwd = "****" if mask_password else self.password
            return f"rtsp://{self.user}:{pwd}@{self.host}:{self.port}{self.path}"
        return f"rtsp://{self.host}:{self.port}{self.path}"

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True, name="CCTV-Capture-Thread")
        self.thread.start()
        logger.info(f"Streamer thread started for {self.get_rtsp_url(mask_password=True)}")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        self.connected = False
        self.latest_jpeg = None
        self.latest_frame = None
        logger.info("Streamer thread stopped (camera connection closed)")

    def _capture_loop(self):
        # Force low-latency TCP and disable ffmpeg buffering
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|max_delay;100000|reorder_queue_size;0"

        fps_timer = time.time()
        fps_frame_count = 0
        encode_interval = 1.0 / max(1, self.target_fps)
        last_encode_time = 0

        while self.running:
            rtsp_url = self.get_rtsp_url(mask_password=False)
            logger.info(f"Connecting to RTSP stream (on-demand low-latency): {self.get_rtsp_url(mask_password=True)}")

            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                self.connected = False
                self.last_error = "Failed to open RTSP stream"
                self.reconnect_count += 1
                logger.warning(f"Unable to open RTSP stream. Retrying in 2s... (attempt {self.reconnect_count})")
                time.sleep(2.0)
                continue

            self.connected = True
            self.last_error = None
            logger.info("RTSP stream successfully connected!")

            while self.running:
                # 1. Grab packet immediately without decoding (takes ~0.05ms)
                # This drains the socket buffer at wire speed and prevents ANY queue buildup!
                ret = cap.grab()
                if not ret:
                    logger.warning("RTSP packet grab failed. Reconnecting...")
                    self.connected = False
                    self.reconnect_count += 1
                    break

                now = time.time()

                # 2. Only decode (retrieve) and encode at target_fps
                if now - last_encode_time >= encode_interval:
                    last_encode_time = now

                    # Decode ONLY the freshest frame that was just grabbed!
                    ret_frame, frame = cap.retrieve()
                    if not ret_frame or frame is None:
                        continue

                    h, w = frame.shape[:2]
                    self.resolution = f"{w}x{h}"

                    # Downscale for web transmission efficiency
                    if self.stream_width > 0 and w > self.stream_width:
                        new_h = int(h * (self.stream_width / w))
                        encoded_frame = cv2.resize(frame, (self.stream_width, new_h), interpolation=cv2.INTER_AREA)
                    else:
                        encoded_frame = frame

                    # Encode to JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.stream_quality]
                    success, jpeg = cv2.imencode(".jpg", encoded_frame, encode_param)

                    if success:
                        with self.lock:
                            self.latest_jpeg = jpeg.tobytes()
                            self.latest_frame = frame
                            self.latest_frame_time = now
                            self.total_frames += 1

                    # Calculate measured FPS
                    fps_frame_count += 1
                    elapsed = now - fps_timer
                    if elapsed >= 1.0:
                        self.measured_fps = round(fps_frame_count / elapsed, 1)
                        fps_frame_count = 0
                        fps_timer = now

            cap.release()
            self.connected = False
            time.sleep(0.5)

    def get_snapshot(self):
        """
        Returns the freshest JPEG bytes. If streamer is idle, grabs a single fresh frame on-demand.
        """
        with self.lock:
            if self.running and self.latest_jpeg is not None:
                return self.latest_jpeg

        # Standalone single frame grab if streamer is idle
        try:
            rtsp_url = self.get_rtsp_url(mask_password=False)
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if cap.isOpened():
                for _ in range(4):
                    cap.grab()
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    if self.stream_width > 0 and w > self.stream_width:
                        new_h = int(h * (self.stream_width / w))
                        frame = cv2.resize(frame, (self.stream_width, new_h), interpolation=cv2.INTER_AREA)
                    success, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.stream_quality])
                    if success:
                        return jpeg.tobytes()
        except Exception as e:
            logger.error(f"Error capturing on-demand snapshot: {e}")

        return self._generate_blank_frame("Camera Idle - No Signal")

    def generate_mjpeg_stream(self):
        """
        Generator for FastAPI StreamingResponse (multipart/x-mixed-replace).
        Runs strictly on-demand: automatically starts RTSP capture when viewer connects,
        and stops RTSP capture when viewer disconnects.
        """
        self.add_viewer()
        frame_interval = 1.0 / max(1, self.target_fps)
        last_sent_time = 0

        # Wait briefly for initial frame if stream just spun up
        wait_start = time.time()
        while self.latest_jpeg is None and time.time() - wait_start < 2.5:
            time.sleep(0.1)

        try:
            while self.running:
                now = time.time()
                if now - last_sent_time < frame_interval:
                    time.sleep(0.01)
                    continue

                jpeg_bytes = None
                with self.lock:
                    if self.latest_jpeg is not None:
                        jpeg_bytes = self.latest_jpeg

                if jpeg_bytes is None:
                    jpeg_bytes = self._generate_blank_frame("Connecting to CCTV...")
                    time.sleep(0.3)

                last_sent_time = time.time()

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n\r\n"
                    + jpeg_bytes
                    + b"\r\n"
                )
        except (GeneratorExit, Exception) as e:
            logger.info(f"Stream client disconnected: {type(e).__name__}")
        finally:
            self.remove_viewer()

    def _generate_blank_frame(self, text="No Signal"):
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        blank[:] = (26, 26, 36)  # Dark slate background
        cv2.putText(
            blank,
            text,
            (80, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 165, 255),
            2,
            cv2.LINE_AA,
        )
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            blank,
            timestamp,
            (80, 280),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        _, jpeg = cv2.imencode(".jpg", blank)
        return jpeg.tobytes()

    def get_status(self):
        age = time.time() - self.latest_frame_time if self.latest_frame_time > 0 else -1
        is_streaming = self.running and self.connected and (age >= 0 and age < 5.0)
        return {
            "status": "streaming" if is_streaming else ("idle" if not self.running else "connecting"),
            "running": self.running,
            "connected": self.connected,
            "active_viewers": self.active_viewers,
            "measured_fps": self.measured_fps if is_streaming else 0.0,
            "target_fps": self.target_fps,
            "resolution": self.resolution,
            "last_frame_age_sec": round(age, 2) if age >= 0 else None,
            "total_frames": self.total_frames,
            "reconnect_count": self.reconnect_count,
            "last_error": self.last_error,
            "rtsp_url": self.get_rtsp_url(mask_password=True),
        }
