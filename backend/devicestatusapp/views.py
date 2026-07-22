import json
import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone  # <--- PENTING: Tambahkan import ini
from .models import DeviceState, DoorStatusLog
import os
import shutil
import imageio

# --- View untuk Get Status Pintu (Door Panel) ---
def get_door_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Door Panel").first()
            
            if device:
                # Konversi waktu server ke Waktu Lokal (Asia/Jakarta)
                local_time = timezone.localtime(device.last_updated)
                
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S") # Format jam lokal
                })
            else:
                return JsonResponse({
                    "device": "Door Panel", 
                    "status": "Closed",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status PLN ---
def get_pln_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="PLN").first()
            
            if device:
                # Konversi waktu server ke Waktu Lokal (Asia/Jakarta)
                local_time = timezone.localtime(device.last_updated)

                return JsonResponse({
                    "device": "PLN",
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S") # Format jam lokal
                })
            else:
                return JsonResponse({
                    "device": "PLN", 
                    "status": "Inactive",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status Motion Sensor 1 ---
def get_motion1_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 1").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 1", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status Motion Sensor 2 ---
def get_motion2_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 2").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 2", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Streaming CCTV RTSP (Integrasi Lokal) ---
import cv2
import time
from django.http import StreamingHttpResponse

_yolo_model = None

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Load YOLOv8 nano model (downloads standard yolov8n.pt if not present)
            _yolo_model = YOLO("yolov8n.pt")
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            return None
    return _yolo_model

def gen_cctv(src="cctv", detect=False):
    import os
    # Paksa RTSP menggunakan TCP (bukan UDP) agar tidak ada packet loss di jalur VPN
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    if src == "cctv2":
        rtsp_url = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"
    else:
        rtsp_url = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"
        
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    frame_count = 0
    last_boxes = [] # List of tuples: (x1, y1, x2, y2, conf)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                time.sleep(1)
                cap = cv2.VideoCapture(rtsp_url)
                continue
            
            frame_count += 1
            
            # Perkecil resolusi agar beban CPU lokal & bandwidth lebih ringan
            h, w = frame.shape[:2]
            if w > 1280:
                frame = cv2.resize(frame, (1280, int(h * (1280 / w))))
                # recalculate width/height if resized
                h, w = frame.shape[:2]
            
            # Deteksi orang dengan YOLO jika diaktifkan
            if detect:
                # Lakukan deteksi setiap 3 frame untuk menghemat CPU
                if frame_count % 3 == 0 or len(last_boxes) == 0:
                    model = get_yolo_model()
                    if model is not None:
                        # classes=[0] filter hanya mendeteksi "person"
                        results = model(frame, classes=[0], conf=0.4, verbose=False)
                        last_boxes = []
                        for r in results:
                            for box in r.boxes:
                                x1, y1, x2, y2 = box.xyxy[0]
                                conf = float(box.conf[0])
                                last_boxes.append((int(x1), int(y1), int(x2), int(y2), conf))
                
                # Gambar bounding box di frame
                for (x1, y1, x2, y2, conf) in last_boxes:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    label = f"Person {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
            # Encode frame ke JPEG dengan kualitas 70%
            _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            
            # Batasi frame rate ke kisaran ~25 FPS agar tidak menghabiskan daya CPU
            time.sleep(0.04)
    finally:
        cap.release()

def cctv_stream(request):
    src = request.GET.get("src", "cctv")
    detect = request.GET.get("detect", "false").lower() == "true"
    try:
        return StreamingHttpResponse(gen_cctv(src, detect), content_type="multipart/x-mixed-replace;boundary=frame")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def capture_photo(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    
    src = request.GET.get("src", "cctv")
    if src == "cctv2":
        rtsp_url = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"
    else:
        rtsp_url = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"

    try:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            return JsonResponse({"error": f"Failed to open camera stream {src}"}, status=500)

        # Skip a few frames to let the decoder settle
        for _ in range(5):
            cap.grab()

        ret, frame = cap.retrieve()
        cap.release()

        if not ret:
            return JsonResponse({"error": "Failed to retrieve frame from camera"}, status=500)

        # Ensure output directory exists
        output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
        os.makedirs(output_dir, exist_ok=True)

        # Draw YOLO detection on captured image if detect parameter is true
        detect = request.GET.get("detect", "false").lower() == "true"
        if detect:
            model = get_yolo_model()
            if model is not None:
                results = model(frame, classes=[0], conf=0.4, verbose=False)
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = box.xyxy[0]
                        conf = float(box.conf[0])
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        label = f"Person {conf:.2f}"
                        cv2.putText(frame, label, (int(x1), int(y1) - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Save single historical image (no latest file clone)
        now = timezone.now()
        filename = f"{src}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, frame)

        formatted_time = now.strftime("%b %d, %I:%M %p")

        return JsonResponse({
            "status": "success",
            "url": f"/media/cctv/photos/{filename}",
            "timestamp": now.isoformat(),
            "formatted_time": formatted_time
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def capture_video(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    src = request.GET.get("src", "cctv")
    if src == "cctv2":
        rtsp_url = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"
    else:
        rtsp_url = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"

    output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "videos")
    os.makedirs(output_dir, exist_ok=True)

    now = timezone.now()
    filename = f"{src}_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
    filepath = os.path.join(output_dir, filename)

    detect = request.GET.get("detect", "false").lower() == "true"
    recorded_with_ffmpeg = False
    photo_url = None

    # Try FFmpeg capture first if detect is False (allows video + audio capture)
    if not detect:
        try:
            import subprocess
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            # Record for 10 seconds, copy video stream, encode audio to AAC
            cmd = [
                ffmpeg_exe,
                "-y",
                "-rtsp_transport", "tcp",
                "-t", "10",
                "-i", rtsp_url,
                "-c:v", "copy",
                "-c:a", "aac",
                filepath
            ]
            
            # Run with a 15 second timeout so it doesn't block forever
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            
            if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                recorded_with_ffmpeg = True
                
                # Extract first frame from recorded video as companion photo thumbnail
                cap_vid = cv2.VideoCapture(filepath)
                if cap_vid.isOpened():
                    ret, first_frame = cap_vid.read()
                    cap_vid.release()
                    if ret:
                        photo_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
                        os.makedirs(photo_dir, exist_ok=True)
                        photo_filename = f"{src}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                        cv2.imwrite(os.path.join(photo_dir, photo_filename), first_frame)
                        photo_url = f"/media/cctv/photos/{photo_filename}"
        except Exception as ffmpeg_err:
            pass

    # Fallback to OpenCV frame-by-frame capture (No audio) if ffmpeg failed or detect is True
    if not recorded_with_ffmpeg:
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                return JsonResponse({"error": f"Failed to open camera stream {src}"}, status=500)

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 15
            if fps <= 0 or fps > 60:
                fps = 15

            if width > 1280:
                height = int(height * (1280 / width))
                width = 1280

            # Initialize imageio writer with h264 codec for HTML5 native video tags
            writer = imageio.get_writer(filepath, fps=fps, codec='h264', quality=8)

            start_time = time.time()
            duration = 10.0 # 10 seconds
            model = get_yolo_model() if detect else None

            frame_count = 0
            last_boxes = []
            first_frame = None

            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                fh, fw = frame.shape[:2]
                if fw != width or fh != height:
                    frame = cv2.resize(frame, (width, height))

                if detect and model is not None:
                    if frame_count % 3 == 0 or len(last_boxes) == 0:
                        results = model(frame, classes=[0], conf=0.4, verbose=False)
                        last_boxes = []
                        for r in results:
                            for box in r.boxes:
                                x1, y1, x2, y2 = box.xyxy[0]
                                conf = float(box.conf[0])
                                last_boxes.append((int(x1), int(y1), int(x2), int(y2), conf))
                    
                    for (x1, y1, x2, y2, conf) in last_boxes:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"Person {conf:.2f}"
                        cv2.putText(frame, label, (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                if first_frame is None:
                    first_frame = frame.copy()

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                writer.append_data(frame_rgb)
                time.sleep(1 / fps)

            cap.release()
            writer.close()

            # Save companion first frame photo as thumbnail
            if first_frame is not None:
                photo_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
                os.makedirs(photo_dir, exist_ok=True)
                photo_filename = f"{src}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(os.path.join(photo_dir, photo_filename), first_frame)
                photo_url = f"/media/cctv/photos/{photo_filename}"
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    formatted_time = now.strftime("%b %d, %I:%M %p")

    return JsonResponse({
        "status": "success",
        "url": f"/media/cctv/videos/{filename}",
        "photo_url": photo_url,
        "timestamp": now.isoformat(),
        "formatted_time": formatted_time
    })

def cctv_latest(request):
    def get_latest_media(src, folder, extension):
        directory = os.path.join(settings.MEDIA_ROOT, "cctv", folder)
        if not os.path.exists(directory):
            return None, "-", None
        files = [f for f in os.listdir(directory) if f.startswith(src) and f.endswith(extension) and "_latest" not in f and "_auto_" not in f]
        if not files:
            return None, "-", None
        # Sort lexicographically so newest timestamp is last
        files.sort()
        latest_file = files[-1]
        
        # Extract timestamp string from filename e.g. "cctv_20260721_092800.mp4" -> "20260721_092800"
        ts_str = ""
        parts = os.path.splitext(latest_file)[0].split('_')
        if len(parts) >= 3:
            ts_str = parts[1] + "_" + parts[2]
        elif len(parts) >= 2:
            ts_str = parts[1]
            
        filepath = os.path.join(directory, latest_file)
        mtime = os.path.getmtime(filepath)
        dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
        formatted_time = dt.strftime("%b %d, %I:%M %p")
        
        return f"/media/cctv/{folder}/{latest_file}", formatted_time, ts_str

    response_data = {}
    for src in ["cctv", "cctv2"]:
        photo_url, photo_time, photo_ts = get_latest_media(src, "photos", ".jpg")
        video_url, _, video_ts = get_latest_media(src, "videos", ".mp4")

        # If video is older than photo, hide the video URL (reset to None)
        if video_ts and photo_ts and video_ts < photo_ts:
            video_url = None

        response_data[src] = {
            "photo_url": photo_url,
            "video_url": video_url,
            "formatted_time": photo_time
        }
        
    return JsonResponse(response_data)

@csrf_exempt
def cctv_history(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)
        
    media_type = request.GET.get("type", "photos") # "photos" or "videos"
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

    folder = "photos" if media_type == "photos" else "videos"
    extension = ".jpg" if media_type == "photos" else ".mp4"
    directory = os.path.join(settings.MEDIA_ROOT, "cctv", folder)

    if not os.path.exists(directory):
        return JsonResponse({
            "items": [],
            "total_count": 0,
            "total_pages": 0,
            "current_page": page
        })

    # List all files matching filter
    files = [f for f in os.listdir(directory) if f.endswith(extension) and "_latest" not in f]
    
    # Compile metadata for each file
    items = []
    for f in files:
        filepath = os.path.join(directory, f)
        mtime = os.path.getmtime(filepath)
        dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
        
        # Parse camera name
        cam_label = "Kamera #1"
        if f.startswith("cctv2"):
            cam_label = "Kamera #2"
            
        # Parse file size in KB
        size_bytes = os.path.getsize(filepath)
        size_kb = f"{round(size_bytes / 1024)} KB"
        
        # Formatted time e.g. "21 Jul 09:26 AM"
        formatted_time = dt.strftime("%d %b %I:%M %p")
        
        items.append({
            "name": f,
            "url": f"/media/cctv/{folder}/{f}",
            "camera": cam_label,
            "timestamp": formatted_time,
            "size": size_kb,
            "mtime": mtime
        })

    # Sort descending by file modification time (newest first)
    items.sort(key=lambda x: x["mtime"], reverse=True)

    # Paginate
    total_count = len(items)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_items = items[start_idx:end_idx]
    
    import math
    total_pages = math.ceil(total_count / limit)

    return JsonResponse({
        "items": paginated_items,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    })

@csrf_exempt
def cctv_alerts(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)
        
    directory = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
    if not os.path.exists(directory):
        return JsonResponse([], safe=False)
        
    # List files ending in .jpg and containing _auto_ in filename
    files = [f for f in os.listdir(directory) if f.endswith(".jpg") and "_auto_" in f]
    
    alerts = []
    for f in files:
        filepath = os.path.join(directory, f)
        mtime = os.path.getmtime(filepath)
        dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
        
        cam_label = "Kamera #1"
        if f.startswith("cctv2"):
            cam_label = "Kamera #2"
            
        formatted_time = dt.strftime("%d %b %I:%M %p")
        
        alerts.append({
            "id": f,
            "camera": cam_label,
            "url": f"/media/cctv/photos/{f}",
            "timestamp": formatted_time,
            "raw_time": dt.isoformat()
        })
        
    # Sort descending by timestamp (newest first)
    alerts.sort(key=lambda x: x["raw_time"], reverse=True)
    
    # Return top 10 alerts
    return JsonResponse(alerts[:10], safe=False)

def get_door_logs(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)

    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 5))

    # Auto-seed initial sample log data if empty so UI looks filled right away
    if DoorStatusLog.objects.count() == 0:
        now = timezone.now()
        sample_events = [
            ("OPEN", now - timezone.timedelta(minutes=5)),
            ("CLOSE", now - timezone.timedelta(minutes=15)),
            ("OPEN", now - timezone.timedelta(minutes=30)),
            ("CLOSE", now - timezone.timedelta(hours=1)),
            ("OPEN", now - timezone.timedelta(hours=2)),
        ]
        for st, ts in sample_events:
            DoorStatusLog.objects.create(status=st, timestamp=ts)

    qs = DoorStatusLog.objects.order_by("-timestamp")
    total_count = qs.count()

    import math
    total_pages = math.ceil(total_count / limit) or 1

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    logs_page = qs[start_idx:end_idx]

    # Current overall door status
    door_device = DeviceState.objects.filter(device_name="Door Panel").first()
    current_status = "CLOSED"
    if door_device:
        current_status = "OPEN" if door_device.status == "Open" else "CLOSE"
    elif qs.exists():
        current_status = qs.first().status

    items = []
    for log in logs_page:
        local_time = timezone.localtime(log.timestamp)
        items.append({
            "id": log.id,
            "status": log.status,
            "timestamp": local_time.strftime("%b %d, %I:%M %p")
        })

    return JsonResponse({
        "current_status": current_status,
        "logs": items,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    })