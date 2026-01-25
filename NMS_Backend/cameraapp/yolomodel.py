from ultralytics import YOLO
from django.conf import settings
import os
import cv2
import numpy as np
import requests

MODEL_PATH = os.path.join(settings.BASE_DIR, "weights", "cleanliness.pt") 

model = YOLO(MODEL_PATH)
DIRTY_CLASSES = {"dryleaves", "grass", "tree"}

def classify_from_endpoint(image_url: str):
    response = requests.get(image_url, timeout=10)
    if response.status_code != 200:
        raise RuntimeError("Gagal mengambil gambar")

    image_array = np.frombuffer(response.content, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if frame is None:
        raise RuntimeError("Frame tidak valid")

    # ROI MASKING
    h, w, _ = frame.shape
    x1, y1 = int(0.55 * w), int(0.25 * h)
    frame[y1:h, x1:w] = 0

    # YOLO Prediction
    results = model.predict(frame, verbose=False)
    
    # --- BAGIAN YANG DIPERBAIKI ---
    
    # Cek apakah ini model klasifikasi atau deteksi
    if results[0].probs is not None:
        # LOGIKA KLASIFIKASI (Jika Anda mengganti model ke tipe -cls nantinya)
        probs = results[0].probs
        class_id = probs.top1
        confidence = float(probs.top1conf)
        class_name = model.names[class_id].lower()
        status = "kotor" if class_name in DIRTY_CLASSES else "bersih"
        
    else:
        # LOGIKA DETEKSI OBJEK (Untuk model yang Anda pakai sekarang)
        boxes = results[0].boxes
        
        detected_dirty_objects = []
        highest_conf = 0.0
        
        # Loop semua kotak yang terdeteksi
        for box in boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id].lower()
            conf = float(box.conf[0])
            
            # Jika objek yang terdeteksi termasuk kategori kotor
            if class_name in DIRTY_CLASSES:
                detected_dirty_objects.append(class_name)
                if conf > highest_conf:
                    highest_conf = conf

        # Tentukan status akhir
        if len(detected_dirty_objects) > 0:
            status = "kotor"
            class_name = detected_dirty_objects[0] # Ambil salah satu objek kotor
            confidence = highest_conf
        else:
            status = "bersih"
            class_name = "clean_area"
            confidence = 1.0 # Anggap 100% bersih jika tidak ada objek kotor

    return {
        "status": status,
        "class": class_name,
        "confidence": confidence
    }