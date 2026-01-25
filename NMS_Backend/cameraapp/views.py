from django.http import JsonResponse ,StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from django.conf import settings
import cv2
from django.http import HttpResponse
from tests import MODEL
from .tapo_ptz import move_ptz1, move_ptz2
from datetime import datetime
import time
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .yolomodel import classify_from_endpoint
from ultralytics import YOLO
import numpy as np
from .camera_logic import CAMERA_STATES, TapoEventListener
import traceback
import requests

MODEL_PATH = os.path.join(settings.BASE_DIR, "weights", "person-fire.pt") 
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None
SESSION_CAM1 = "camera_ai"
SESSION_CAM2 = "camera_raw"
camera = None
# Definisi logic bisnis
DIRTY_CLASSES = {"dryleaves", "grass", "tree"}
# ---- PTZ API ----
@csrf_exempt
def ptz_control(request):
    cam1 = request.session.get(SESSION_CAM1)
    if not cam1:
        return JsonResponse({"error": "Camera not connected"}, status=400)

    data = json.loads(request.body)
    direction = data.get("direction")

    if direction == "left":
        move_ptz1(cam1, -0.5, 0)
    elif direction == "right":
        move_ptz1(cam1, 0.5, 0)
    elif direction == "up":
        move_ptz1(cam1, 0, 0.5)
    elif direction == "down":
        move_ptz1(cam1, 0, -0.5)
    else:
        return JsonResponse({"error": "Unknown direction"}, status=400)

    return JsonResponse({"status": "ok", "moved": direction})

@csrf_exempt
def ptz_control2(request):
    cam2 = request.session.get(SESSION_CAM2)
    if not cam2:
        return JsonResponse({"error": "Camera not connected"}, status=400)

    data = json.loads(request.body)
    direction = data.get("direction")

    if direction == "left":
        move_ptz2(cam2, -0.5, 0)
    elif direction == "right":
        move_ptz2(cam2, 0.5, 0)
    elif direction == "up":
        move_ptz2(cam2, 0, 0.5)
    elif direction == "down":
        move_ptz2(cam2, 0, -0.5)
    else:
        return JsonResponse({"error": "Unknown direction"}, status=400)

    return JsonResponse({"status": "ok", "moved": direction})


@csrf_exempt
def connect_camera(request):
    data = json.loads(request.body)

    rtsp_url = f"rtsp://{data['username']}:{data['password']}@{data['ip']}:554/stream1"
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        return JsonResponse({"message": "Failed to connect"}, status=400)

    cap.release()

    request.session[SESSION_CAM1] = data
    return JsonResponse({"message": "Camera AI connected"})

@csrf_exempt
def connect_camera2(request):
    data = json.loads(request.body)
    
    # ... Logika validasi koneksi RTSP kamu yang lama ...
    rtsp_url = f"rtsp://{data['username2']}:{data['password2']}@{data['ip2']}:554/stream1"
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return JsonResponse({"message": "Failed to connect"}, status=400)
    cap.release()

    request.session[SESSION_CAM2] = data
    
    # --- TAMBAHAN BARU: Mulai Listener Thread ---
    # Kita gunakan SESSION_CAM1 sebagai key unik
    listener = TapoEventListener(
        ip2=data['ip2'], 
        user2=data['username2'], 
        password2=data['password2'],
        session_key=SESSION_CAM2
    )
    listener.start()
    # ---------------------------------------------

    return JsonResponse({"message": "Camera AI connected & Listening for Events"})

# Endpoint baru untuk React mengecek notifikasi
@api_view(['GET'])
def check_notifications(request):
    # Cek apakah ada notifikasi untuk SESSION_CAM1
    state = CAMERA_STATES.get(SESSION_CAM2)
    
    if state:
        # Kita kirim notif jika event terjadi kurang dari 5 detik lalu
        if time.time() - state['timestamp'] < 5:
            return Response({
                "has_alert": True,
                "message": state['message'],
                "is_recording": state.get('is_recording', False)
            })
            
    return Response({"has_alert": False})

def detect_person(frame, conf=0.3):
    results = model(frame, conf=conf, verbose=False)[0]

    person_count = 0

    if results.boxes is not None:
        for box in results.boxes:
            cls = int(box.cls)
            label = model.names[cls].lower()

            if label != "person":
                continue

            person_count += 1

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf)

            # DRAW BOX
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"Person {confidence:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    return frame, person_count


def video_stream(request):
    cam = request.session.get(SESSION_CAM1)
    if not cam:
        return HttpResponse("Camera AI not connected", status=400)

    rtsp_url = f"rtsp://{cam['username']}:{cam['password']}@{cam['ip']}:554/stream1"
    cap = cv2.VideoCapture(rtsp_url)

    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (640, 360))
            frame, person_count = detect_person(frame)

            cv2.putText(
                frame,
                f"AI PERSON: {person_count}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )

            _, jpeg = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )

        cap.release()

    return StreamingHttpResponse(generate(), content_type="multipart/x-mixed-replace; boundary=frame")


# Tambahan untuk stream2 jika ini dihapus

def video_stream2(request):
    cam = request.session.get(SESSION_CAM2)
    if not cam:
        return HttpResponse("Camera RAW not connected", status=400)

    rtsp_url = f"rtsp://{cam['username2']}:{cam['password2']}@{cam['ip2']}:554/stream2"
    cap = cv2.VideoCapture(rtsp_url)

    def generate():
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (640, 360))

            _, jpeg = cv2.imencode(".jpg", frame)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )

        cap.release()

    return StreamingHttpResponse(generate(), content_type="multipart/x-mixed-replace; boundary=frame")


def camera_screenshot(request):
    # 1. Validation
    cam = request.session.get("camera")
    if not cam: 
        return JsonResponse({"error": "No cam session data"}, status=400)

    # Ensure model is globally loaded
    if 'model' not in globals() or model is None:
        return JsonResponse({"error": "Model AI not loaded properly"}, status=500)

    # 2. Capture RTSP
    rtsp_url = f"rtsp://{cam['username']}:{cam['password']}@{cam['ip']}:554/stream1"
    
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        return JsonResponse({"error": "Cannot open RTSP stream"}, status=500)

    success, frame = cap.read()
    cap.release() 

    if not success:
        return JsonResponse({"error": "Failed to capture frame"}, status=500)

    # 3. ROI Masking & Prediction
    frame_for_ai = frame.copy()
    h, w, _ = frame.shape
    x1, y1 = int(0.55 * w), int(0.25 * h)
    x2, y2 = w, h
    frame_for_ai[y1:y2, x1:x2] = 0 

    # Predict
    results = model.predict(frame_for_ai, verbose=False) 
    result = results[0] # Get the first result

    # --- FIX STARTS HERE ---
    
    # Case A: Model is Classification (Has probs)
    if result.probs is not None:
        class_id = result.probs.top1
        raw_class_name = model.names[class_id].lower()
        confidence = result.probs.top1conf.item()

    # Case B: Model is Object Detection (Has boxes, but no probs)
    elif result.boxes is not None:
        # Fallback logic: If detection model, take the object with highest confidence
        if len(result.boxes) > 0:
            # Sort by confidence and take top 1
            best_box = sorted(result.boxes, key=lambda x: x.conf[0], reverse=True)[0]
            class_id = int(best_box.cls[0])
            raw_class_name = model.names[class_id].lower()
            confidence = float(best_box.conf[0])
        else:
            # No objects detected
            raw_class_name = "unknown"
            confidence = 0.0

    else:
        return JsonResponse({"error": "Model output format not recognized (No probs or boxes)"}, status=500)

    # --- LOGIC CONTINUES ---

    if raw_class_name in DIRTY_CLASSES:
        final_status = "KOTOR"
        color = (0, 0, 255) # Red
    else:
        final_status = "BERSIH"
        color = (0, 255, 0) # Green

    # Draw Label
    label_text = f"Site: {final_status} | Det: {raw_class_name} ({confidence:.1%})"
    cv2.putText(frame, label_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)

    # Save File
    filename = f"{final_status}_{raw_class_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    save_dir = os.path.join(settings.MEDIA_ROOT, "screenshots")
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    save_path = os.path.join(save_dir, filename)
    cv2.imwrite(save_path, frame)
    
    return JsonResponse({
        "status": "success", 
        "file_url": settings.MEDIA_URL + "screenshots/" + filename, 
        "site_status": final_status,
        "detected_object": raw_class_name,
        "confidence": f"{confidence:.2%}"
    })

@api_view(["POST"])
def classify_site(request):
    image_url = request.data.get("image_url")

    if not image_url:
        return Response(
            {"error": "image_url wajib diisi"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        result = classify_from_endpoint(image_url)
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )