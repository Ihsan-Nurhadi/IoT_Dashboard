import json
import paho.mqtt.client as mqtt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone  # <--- PENTING: Tambahkan import ini
from .models import DeviceState, DoorStatusLog, CCTVCamera
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

# --- View untuk Get Status Motion Sensor 3 ---
def get_motion3_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 3").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 3", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Get Status Motion Sensor 4 ---
def get_motion4_status(request):
    if request.method == "GET":
        try:
            device = DeviceState.objects.filter(device_name="Motion Sensor 4").first()
            if device:
                local_time = timezone.localtime(device.last_updated)
                return JsonResponse({
                    "device": device.device_name,
                    "status": device.status, 
                    "last_updated": local_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            else:
                return JsonResponse({
                    "device": "Motion Sensor 4", 
                    "status": "Standby",
                    "last_updated": "-"
                })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "GET only"}, status=405)

# --- View untuk Streaming CCTV RTSP (Integrasi Lokal) ---
import cv2
import time
import numpy as np
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

def get_camera_config_for_src(src):
    try:
        cam = CCTVCamera.objects.filter(camera_id=src).first()
    except Exception:
        cam = None

    if cam and cam.is_active:
        rtsp_url = cam.rtsp_url
        if cam.username and cam.password and "@" not in rtsp_url and "rtsp://" in rtsp_url:
            rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{cam.username}:{cam.password}@")
        return rtsp_url, cam
    else:
        if src == "cctv2":
            rtsp_url = "rtsp://nykws2:nykworkshop@10.10.0.5:555/stream1"
        else:
            rtsp_url = "rtsp://nykws1:nykworkshop@10.10.0.5:554/stream1"
        return rtsp_url, None

def draw_detection_zones_on_frame(frame, cam, scores=None):
    if not cam:
        return
    try:
        h, w = frame.shape[:2]
        zones = json.loads(cam.detection_zones or '[]')
        for zone in zones:
            points = zone.get('points', [])
            name = zone.get('name', 'Antenna')
            
            score = None
            if scores and name in scores:
                score = scores[name]
                
            if len(points) >= 3:
                pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in points], dtype=np.int32)
                pts = pts.reshape((-1, 1, 2))
                
                # Default cyan/yellow colors
                poly_color = (255, 255, 0)
                text_color = (255, 255, 0)
                
                if score is not None:
                    # Red color for stolen zones
                    if score < 0.55:
                        poly_color = (0, 0, 255)
                        text_color = (0, 0, 255)
                    else:
                        poly_color = (255, 255, 0)
                        text_color = (255, 255, 0)
                
                cv2.polylines(frame, [pts], isClosed=True, color=poly_color, thickness=2)
                
                display_name = name
                if score is not None:
                    # Format as 2 decimal places (e.g. 0,99) to show precise match values
                    score_str = f"{score:.2f}".replace(".", ",")
                    display_name += f" ({score_str})"
                    
                label_x = pts[0][0][0]
                label_y = pts[0][0][1] - 8
                cv2.putText(frame, display_name, (label_x, max(label_y, 15)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
    except Exception as e:
        print(f"Error drawing detection zones: {e}")

def gen_cctv(src="cctv", detect=False):
    import os
    # Paksa RTSP menggunakan TCP (bukan UDP) agar tidak ada packet loss di jalur VPN
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    
    rtsp_url, cam = get_camera_config_for_src(src)
        
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
            
            draw_detection_zones_on_frame(frame, cam)
            
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
    rtsp_url, cam = get_camera_config_for_src(src)

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

        # 1. Run Template Matching Verification against Baselines
        import glob
        zones = []
        if cam:
            try:
                zones = json.loads(cam.detection_zones or '[]')
            except Exception:
                pass

        baselines_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
        scores = {}
        antenna_details = []
        stolen_detected = False
        first_stolen_name = None

        h, w = frame.shape[:2]

        for zone in zones:
            name = zone.get('name', '').strip()
            name_slug = name.replace(' ', '_')
            points = zone.get('points', [])
            if not name or len(points) < 3:
                continue

            # Load all baselines for this zone
            pattern = os.path.join(baselines_dir, f"baseline_{src}_{name_slug}*.jpg")
            baseline_paths = glob.glob(pattern)

            best_score = -1.0
            if baseline_paths:
                x_coords = [float(p[0]) for p in points]
                y_coords = [float(p[1]) for p in points]

                xmin = int(min(x_coords) * w)
                xmax = int(max(x_coords) * w)
                ymin = int(min(y_coords) * h)
                ymax = int(max(y_coords) * h)

                w_px = xmax - xmin
                h_px = ymax - ymin

                pad_x = max(25, int(w_px * 0.15))
                pad_y = max(25, int(h_px * 0.15))

                s_xmin = max(0, xmin - pad_x)
                s_xmax = min(w, xmax + pad_x)
                s_ymin = max(0, ymin - pad_y)
                s_ymax = min(h, ymax + pad_y)

                search_region = frame[s_ymin:s_ymax, s_xmin:s_xmax]
                sr_h, sr_w = search_region.shape[:2]

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
                    except Exception:
                        continue

            if best_score >= 0:
                scores[name] = best_score
                is_stolen = best_score < 0.55
                if is_stolen:
                    stolen_detected = True
                    if first_stolen_name is None:
                        first_stolen_name = name
                antenna_details.append({
                    "name": name,
                    "score": float(best_score),
                    "status": "stolen" if is_stolen else "present"
                })
            else:
                scores[name] = None
                antenna_details.append({
                    "name": name,
                    "score": None,
                    "status": "unverified"
                })

        # Draw overlays with similarity scores
        draw_detection_zones_on_frame(frame, cam, scores=scores)

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

        # Save photo: prefix with _stolen_ if any antenna was missing to trigger frontend alerts
        now = timezone.localtime(timezone.now())
        if stolen_detected:
            filename = f"{src}_stolen_{first_stolen_name or 'Antena'}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
        else:
            filename = f"{src}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            
        filepath = os.path.join(output_dir, filename)
        cv2.imwrite(filepath, frame)

        formatted_time = now.strftime("%b %d, %I:%M %p")
        
        total_antennas = len([z for z in antenna_details if z["status"] != "unverified"]) or len(zones)
        present_antennas = len([z for z in antenna_details if z["status"] == "present"])

        return JsonResponse({
            "status": "success",
            "url": f"/media/cctv/photos/{filename}",
            "timestamp": now.isoformat(),
            "formatted_time": formatted_time,
            "antenna_check": {
                "checked": len(antenna_details) > 0,
                "total": total_antennas,
                "present": present_antennas,
                "stolen_detected": stolen_detected,
                "details": antenna_details
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def capture_video(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    src = request.GET.get("src", "cctv")
    rtsp_url, cam = get_camera_config_for_src(src)

    output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "videos")
    os.makedirs(output_dir, exist_ok=True)

    now = timezone.localtime(timezone.now())
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
                        draw_detection_zones_on_frame(first_frame, cam)
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

                draw_detection_zones_on_frame(frame, cam)

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
        files = [f for f in os.listdir(directory) if f.startswith(src) and f.endswith(extension) and "_latest" not in f]
        if not files:
            return None, "-", None
        # Sort by mtime so newest timestamp is last
        files.sort(key=lambda x: os.path.getmtime(os.path.join(directory, x)))
        latest_file = files[-1]
        
        # Extract numeric timestamp segments dynamically (e.g. ['20260721', '092800'])
        parts = os.path.splitext(latest_file)[0].split('_')
        numeric_parts = [p for p in parts if p.isdigit()]
        ts_str = "_".join(numeric_parts)
            
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
    category = request.GET.get("category", "camera") # "camera" or "sensor"
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
    if media_type == "photos":
        if category == "sensor":
            files = [f for f in os.listdir(directory) if f.endswith(extension) and "_latest" not in f and "_pir_" in f]
        else:
            files = [f for f in os.listdir(directory) if f.endswith(extension) and "_latest" not in f and "_pir_" not in f]
    else:
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
        
    category = request.GET.get("category", "all")
    directory = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
    if not os.path.exists(directory):
        return JsonResponse([], safe=False)
        
    all_files = os.listdir(directory)
    
    alerts = []
    
    # 1. Camera YOLO Alerts (_auto_)
    if category in ["all", "camera"]:
        auto_files = [f for f in all_files if f.endswith(".jpg") and "_auto_" in f]
        for f in auto_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
            
            cam_label = "Kamera #1"
            if f.startswith("cctv2"):
                cam_label = "Kamera #2"
                
            formatted_time = dt.strftime("%d %b %I:%M %p")
            
            alerts.append({
                "id": f,
                "type": "camera",
                "camera": cam_label,
                "title": f"Orang terdeteksi di {cam_label}",
                "url": f"/media/cctv/photos/{f}",
                "timestamp": formatted_time,
                "raw_time": dt.isoformat()
            })

    # 2. PIR Motion Sensor Alerts (_pir_) - Grouped by timestamp so 2 camera snapshots produce ONLY 1 alert
    if category in ["all", "pir"]:
        pir_files = [f for f in all_files if f.endswith(".jpg") and "_pir_" in f]
        pir_groups = {}
        for f in pir_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
            
            parts = os.path.splitext(f)[0].split('_pir_')
            ts_key = parts[1] if len(parts) > 1 else str(int(mtime))
            
            if ts_key not in pir_groups:
                pir_groups[ts_key] = {
                    "file": f,
                    "mtime": mtime,
                    "dt": dt
                }
                
        for ts_key, data in pir_groups.items():
            f = data["file"]
            dt = data["dt"]
            formatted_time = dt.strftime("%d %b %I:%M %p")
            alerts.append({
                "id": f"pir_{ts_key}",
                "type": "pir",
                "camera": "Sensor PIR",
                "title": "Gerakan terdeteksi Sensor PIR",
                "url": f"/media/cctv/photos/{f}",
                "timestamp": formatted_time,
                "raw_time": dt.isoformat()
            })
        
    # 3. Camera Stolen Alerts (_stolen_)
    if category in ["all", "stolen", "camera"]:
        stolen_files = [f for f in all_files if f.endswith(".jpg") and "_stolen_" in f]
        for f in stolen_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
            
            parts = f.replace(".jpg", "").split("_stolen_")
            cam_id = parts[0] if len(parts) > 0 else "cctv"
            zone_name = parts[1].split("_")[0] if len(parts) > 1 else "Antenna"
            
            cam_label = cam_id.upper()
            formatted_time = dt.strftime("%d %b %I:%M %p")
            
            alerts.append({
                "id": f,
                "type": "stolen",
                "camera": cam_label,
                "title": f"Antena {zone_name} Hilang / Dicuri di {cam_label}!",
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
            "timestamp": local_time.strftime("%b %d, %I:%M %p"),
            "raw_time": local_time.isoformat()
        })


    return JsonResponse({
        "current_status": current_status,
        "logs": items,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    })

@csrf_exempt
def cctv_detection_logs(request):
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)

    category = request.GET.get("category", "all").lower()  # "all", "gerakan" (pir), "orang" (person)
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

    directory = os.path.join(settings.MEDIA_ROOT, "cctv", "photos")
    if not os.path.exists(directory):
        return JsonResponse({
            "items": [],
            "total_count": 0,
            "total_pages": 1,
            "current_page": page
        })

    all_files = os.listdir(directory)
    items = []

    # Parse optional ISO date range filters
    start_dt = None
    end_dt = None
    if start_date_str:
        try:
            start_dt = timezone.datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        except Exception:
            pass
    if end_date_str:
        try:
            end_dt = timezone.datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except Exception:
            pass

    # 1. Camera Person Detection Logs (_auto_)
    if category in ["all", "orang", "person"]:
        auto_files = [f for f in all_files if f.endswith(".jpg") and "_auto_" in f]
        for f in auto_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())
            
            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue

            cam_label = "Cam 1"
            video_src = "cctv"
            if f.startswith("cctv2"):
                cam_label = "Cam 2"
                video_src = "cctv2"

            # Companion video url if available
            video_url = None
            video_name = f.replace(".jpg", ".mp4")
            video_path = os.path.join(settings.MEDIA_ROOT, "cctv", "videos", video_name)
            if os.path.exists(video_path):
                video_url = f"/media/cctv/videos/{video_name}"

            formatted_time = dt.strftime("%d %b %Y, %I:%M %p")

            items.append({
                "id": f,
                "type": "person",
                "type_label": "Orang x1",
                "camera": cam_label,
                "video_src": video_src,
                "photo_url": f"/media/cctv/photos/{f}",
                "video_url": video_url,
                "timestamp": formatted_time,
                "raw_time": dt.isoformat(),
                "mtime": mtime
            })

    # 2. PIR Motion Sensor Logs (_pir_)
    if category in ["all", "gerakan", "pir", "sensor"]:
        pir_files = [f for f in all_files if f.endswith(".jpg") and "_pir_" in f]
        pir_groups = {}
        for f in pir_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())

            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue

            parts = os.path.splitext(f)[0].split('_pir_')
            ts_key = parts[1] if len(parts) > 1 else str(int(mtime))

            cam_label = "Cam 1"
            video_src = "cctv"
            if f.startswith("cctv2"):
                cam_label = "Cam 2"
                video_src = "cctv2"

            if ts_key not in pir_groups:
                pir_groups[ts_key] = {
                    "file": f,
                    "mtime": mtime,
                    "dt": dt,
                    "camera": cam_label,
                    "video_src": video_src
                }

        for ts_key, data in pir_groups.items():
            f = data["file"]
            dt = data["dt"]
            formatted_time = dt.strftime("%d %b %Y, %I:%M %p")
            items.append({
                "id": f"pir_{ts_key}",
                "type": "motion",
                "type_label": "Motion Detected",
                "camera": data["camera"],
                "video_src": data["video_src"],
                "photo_url": f"/media/cctv/photos/{f}",
                "video_url": None,
                "timestamp": formatted_time,
                "raw_time": dt.isoformat(),
                "mtime": data["mtime"]
            })

    # 3. Camera Stolen Logs (_stolen_)
    if category in ["all", "stolen", "camera"]:
        stolen_files = [f for f in all_files if f.endswith(".jpg") and "_stolen_" in f]
        for f in stolen_files:
            filepath = os.path.join(directory, f)
            mtime = os.path.getmtime(filepath)
            dt = timezone.datetime.fromtimestamp(mtime, tz=timezone.get_current_timezone())

            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue

            parts = f.replace(".jpg", "").split("_stolen_")
            cam_id = parts[0] if len(parts) > 0 else "cctv"
            zone_name = parts[1].split("_")[0] if len(parts) > 1 else "Antenna"
            
            cam_label = cam_id.upper()
            formatted_time = dt.strftime("%d %b %Y, %I:%M %p")

            items.append({
                "id": f,
                "type": "stolen",
                "type_label": f"Antena {zone_name} Hilang",
                "camera": cam_label,
                "video_src": cam_id,
                "photo_url": f"/media/cctv/photos/{f}",
                "video_url": None,
                "timestamp": formatted_time,
                "raw_time": dt.isoformat(),
                "mtime": mtime
            })

    # Sort descending by mtime (newest detection first)
    items.sort(key=lambda x: x["mtime"], reverse=True)

    total_count = len(items)
    import math
    total_pages = math.ceil(total_count / limit) or 1
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_items = items[start_idx:end_idx]

    return JsonResponse({
        "items": paginated_items,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    })


from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from monitoring.views import CsrfExemptSessionAuthentication

@api_view(['GET'])
@permission_classes([AllowAny])
def cameras_list(request):
    cameras = CCTVCamera.objects.all().order_by('camera_id')
    results = []
    for cam in cameras:
        results.append({
            'camera_id': cam.camera_id,
            'camera_name': cam.camera_name,
            'rtsp_url': cam.rtsp_url,
            'onvif_url': cam.onvif_url,
            'username': cam.username,
            'password': cam.password,
            'width': cam.width,
            'height': cam.height,
            'is_active': cam.is_active,
            'detection_zones': json.loads(cam.detection_zones or '[]')
        })
    return JsonResponse(results, safe=False)

@api_view(['GET'])
@permission_classes([AllowAny])
def camera_detail(request, camera_id):
    cam = get_object_or_404(CCTVCamera, camera_id=camera_id)
    return JsonResponse({
        'camera_id': cam.camera_id,
        'camera_name': cam.camera_name,
        'rtsp_url': cam.rtsp_url,
        'onvif_url': cam.onvif_url,
        'username': cam.username,
        'password': cam.password,
        'width': cam.width,
        'height': cam.height,
        'is_active': cam.is_active,
        'detection_zones': json.loads(cam.detection_zones or '[]')
    })

def extract_baseline_templates(camera):
    import cv2
    import os
    import json
    from django.conf import settings
    
    zones = []
    try:
        zones = json.loads(camera.detection_zones or '[]')
    except Exception:
        return
        
    if not zones:
        return
        
    # Look for current camera snapshot
    snapshot_path = os.path.join(settings.MEDIA_ROOT, "cctv", "snapshots", f"snapshot_{camera.camera_id}.jpg")
    frame = None
    
    if os.path.exists(snapshot_path):
        frame = cv2.imread(snapshot_path)
        
    # If snapshot doesn't exist, try capturing from RTSP
    if frame is None:
        rtsp_url = camera.rtsp_url
        if camera.username and camera.password and "@" not in rtsp_url and "rtsp://" in rtsp_url:
            rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{camera.username}:{camera.password}@")
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(rtsp_url)
        if cap.isOpened():
            for _ in range(5):
                cap.grab()
            ret, frame = cap.retrieve()
            cap.release()
            
    if frame is None:
        return
        
    height, width = frame.shape[:2]
    baseline_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
    os.makedirs(baseline_dir, exist_ok=True)
    
    for zone in zones:
        name = zone.get('name', 'Zone').strip().replace(' ', '_')
        points = zone.get('points', [])
        if len(points) < 3:
            continue
            
        x_coords = [float(p[0]) for p in points]
        y_coords = [float(p[1]) for p in points]
        
        xmin = max(0, int(min(x_coords) * width))
        xmax = min(width, int(max(x_coords) * width))
        ymin = max(0, int(min(y_coords) * height))
        ymax = min(height, int(max(y_coords) * height))
        
        if xmax - xmin > 5 and ymax - ymin > 5:
            crop = frame[ymin:ymax, xmin:xmax]
            
            # Determine Time of Day (TOD) using camera database configurations
            from django.utils import timezone
            hour = timezone.localtime().hour
            
            def check_range(h, start, end):
                if start <= end:
                    return start <= h < end
                return h >= start or h < end
                
            if check_range(hour, camera.morning_start, camera.morning_end):
                tod = "morning"
            elif check_range(hour, camera.afternoon_start, camera.afternoon_end):
                tod = "afternoon"
            elif check_range(hour, camera.night_start, camera.night_end):
                tod = "night"
            else:
                tod = "morning"
                
            # Save standard baseline
            filename = f"baseline_{camera.camera_id}_{name}.jpg"
            filepath = os.path.join(baseline_dir, filename)
            cv2.imwrite(filepath, crop)
            
            # Save time-of-day specific baseline to handle daylight/shadow shifts
            tod_filename = f"baseline_{camera.camera_id}_{name}_{tod}.jpg"
            tod_filepath = os.path.join(baseline_dir, tod_filename)
            cv2.imwrite(tod_filepath, crop)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def camera_update(request, camera_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
        
    cam = get_object_or_404(CCTVCamera, camera_id=camera_id)
    data = json.loads(request.body.decode('utf-8'))
    
    cam.camera_name = data.get('camera_name', cam.camera_name)
    cam.rtsp_url = data.get('rtsp_url', cam.rtsp_url)
    cam.onvif_url = data.get('onvif_url', cam.onvif_url)
    cam.username = data.get('username', cam.username)
    
    new_pass = data.get('password')
    if new_pass is not None and new_pass.strip() != "":
        cam.password = new_pass
        
    cam.width = int(data.get('width', cam.width))
    cam.height = int(data.get('height', cam.height))
    cam.is_active = bool(data.get('is_active', cam.is_active))
    
    zones = data.get('detection_zones', [])
    cam.detection_zones = json.dumps(zones)
    cam.save()
    
    # Extract baseline crop templates for CV matching
    extract_baseline_templates(cam)
    
    return JsonResponse({
        'success': True,
        'camera_id': cam.camera_id,
        'detection_zones': zones
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def camera_snapshot(request, camera_id):
    cam = get_object_or_404(CCTVCamera, camera_id=camera_id)
    
    rtsp_url = cam.rtsp_url
    if cam.username and cam.password and "@" not in rtsp_url and "rtsp://" in rtsp_url:
        rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{cam.username}:{cam.password}@")
        
    import cv2
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        return JsonResponse({
            'status': 'error',
            'url': '/contoh cctv.jpg',
            'message': 'Failed to connect to RTSP stream'
        })
        
    for _ in range(5):
        cap.grab()
    ret, frame = cap.retrieve()
    cap.release()
    
    if not ret:
        return JsonResponse({
            'status': 'error',
            'url': '/contoh cctv.jpg',
            'message': 'Failed to retrieve frame from camera'
        })
        
    output_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "snapshots")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"snapshot_{cam.camera_id}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, frame)
    
    return JsonResponse({
        'status': 'success',
        'url': f'/media/cctv/snapshots/{filename}?t={int(time.time())}'
    })

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def camera_create(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    try:
        data = json.loads(request.body.decode('utf-8'))
        camera_id = data.get('camera_id', '').strip()
        if not camera_id:
            return JsonResponse({'error': 'Camera ID must not be empty'}, status=400)
            
        if CCTVCamera.objects.filter(camera_id=camera_id).exists():
            return JsonResponse({'error': f'Camera with ID {camera_id} already exists'}, status=400)
            
        cam = CCTVCamera.objects.create(
            camera_id=camera_id,
            camera_name=data.get('camera_name', camera_id),
            rtsp_url=data.get('rtsp_url', ''),
            onvif_url=data.get('onvif_url'),
            username=data.get('username'),
            password=data.get('password'),
            width=int(data.get('width', 1920)),
            height=int(data.get('height', 1080)),
            is_active=bool(data.get('is_active', True)),
            detection_zones=json.dumps(data.get('detection_zones', []))
        )
        # Extract baseline crop templates for CV matching
        extract_baseline_templates(cam)
        return JsonResponse({'success': True, 'camera_id': cam.camera_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def camera_delete(request, camera_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    cam = get_object_or_404(CCTVCamera, camera_id=camera_id)
    cam.delete()
    return JsonResponse({'success': True})

@csrf_exempt
@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def get_baselines_status(request):
    camera_id = request.GET.get("camera_id")
    if not camera_id:
        return JsonResponse({"error": "camera_id is required"}, status=400)
    
    baselines_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
    status = {
        "morning": False,
        "afternoon": False,
        "night": False
    }
    
    if os.path.exists(baselines_dir):
        import glob
        for tod in ["morning", "afternoon", "night"]:
            pattern = os.path.join(baselines_dir, f"baseline_{camera_id}_*_{tod}.jpg")
            if glob.glob(pattern):
                status[tod] = True
                
    return JsonResponse(status)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def capture_baseline(request):
    data = request.data
    camera_id = data.get("camera_id")
    tod = data.get("tod")
    if not camera_id or not tod:
        return JsonResponse({"error": "camera_id and tod are required"}, status=400)
        
    try:
        camera = CCTVCamera.objects.filter(camera_id=camera_id, is_active=True).first()
        if not camera:
            return JsonResponse({"error": f"Camera {camera_id} not found"}, status=404)
            
        zones = json.loads(camera.detection_zones or '[]')
        if not zones:
            return JsonResponse({"error": "Gambar zona deteksi terlebih dahulu sebelum merekam baseline."}, status=400)
            
        rtsp_url = camera.rtsp_url
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            return JsonResponse({"error": "Failed to connect to camera stream"}, status=500)
            
        for _ in range(5):
            cap.grab()
        ret, frame = cap.retrieve()
        cap.release()
        
        if not ret or frame is None:
            return JsonResponse({"error": "Failed to retrieve frame from camera"}, status=500)
            
        height, width = frame.shape[:2]
        baselines_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
        os.makedirs(baselines_dir, exist_ok=True)
        
        for zone in zones:
            name = zone.get('name', 'Zone').strip().replace(' ', '_')
            points = zone.get('points', [])
            if len(points) < 3:
                continue
                
            x_coords = [float(p[0]) for p in points]
            y_coords = [float(p[1]) for p in points]
            
            xmin = max(0, int(min(x_coords) * width))
            xmax = min(width, int(max(x_coords) * width))
            ymin = max(0, int(min(y_coords) * height))
            ymax = min(height, int(max(y_coords) * height))
            
            if xmax - xmin > 5 and ymax - ymin > 5:
                crop = frame[ymin:ymax, xmin:xmax]
                
                # Save TOD specific baseline
                tod_filename = f"baseline_{camera_id}_{name}_{tod}.jpg"
                cv2.imwrite(os.path.join(baselines_dir, tod_filename), crop)
                
                # Save standard baseline as fallback
                filename = f"baseline_{camera_id}_{name}.jpg"
                cv2.imwrite(os.path.join(baselines_dir, filename), crop)
                
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def delete_baseline(request):
    data = request.data
    camera_id = data.get("camera_id")
    tod = data.get("tod")
    if not camera_id or not tod:
        return JsonResponse({"error": "camera_id and tod are required"}, status=400)
        
    baselines_dir = os.path.join(settings.MEDIA_ROOT, "cctv", "baselines")
    if not os.path.exists(baselines_dir):
        return JsonResponse({"status": "success"})
        
    try:
        import glob
        pattern = os.path.join(baselines_dir, f"baseline_{camera_id}_*_{tod}.jpg")
        for path in glob.glob(pattern):
            try:
                os.remove(path)
            except Exception:
                pass
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)