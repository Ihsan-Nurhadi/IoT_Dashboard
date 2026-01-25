import threading
import time
import cv2
import datetime
import os
from onvif import ONVIFCamera
from django.conf import settings

# Global state untuk notifikasi ke Frontend
# Struktur: {'cam_ip': {'last_event': timestamp, 'is_recording': bool}}
CAMERA_STATES = {}

class TapoEventListener(threading.Thread):
    def __init__(self, ip2, user2, password2, session_key):
        super().__init__()
        self.ip = ip2
        self.user = user2
        self.password = password2
        self.session_key = session_key
        self.running = True
        self.daemon = True # Thread mati jika server mati

    def run(self):
        try:
            # Koneksi ONVIF
            # Pastikan port ONVIF Tapo benar (biasanya 2020)
            cam = ONVIFCamera(self.ip, 2020, self.user, self.password)
            event_service = cam.create_events_service()
            pullpoint = event_service.CreatePullPointSubscription()
            
            print(f"[{self.ip}] Listening for Tapo Events...")

            while self.running:
                try:
                    # Pull messages (Polling event dari kamera)
                    # Timeout singkat agar loop tidak blocking selamanya
                    messages = pullpoint.PullMessages(Timeout='PT2S', MessageLimit=10)
                    
                    for msg in messages:
                        # Analisa XML payload untuk mencari keyword deteksi
                        # Struktur pesan ONVIF sangat dalam, kita ubah ke string untuk pencarian cepat
                        msg_str = str(msg)
                        
                        # LOGIKA DETEKSI: Cek apakah ada event 'Person' atau 'Motion'
                        # Tapo AI detection biasanya mengandung keyword ini di Topic
                        if "RuleEngine" in msg_str and ("Person" in msg_str or "Human" in msg_str):
                             self.trigger_action("Person Detected")
                        
                        # Jika ingin motion biasa:
                        # elif "MotionAlarm" in msg_str and "State: true" in msg_str:
                        #      self.trigger_action("Motion Detected")

                except Exception as e:
                    # Time out itu normal jika tidak ada event
                    pass
                
        except Exception as e:
            print(f"Error on Tapo Listener: {e}")

    def trigger_action(self, label):
        print(f"EVENT TRIGGERED: {label}")
        
        # 1. Update State untuk Notifikasi Frontend
        CAMERA_STATES[self.session_key] = {
            'event': label,
            'timestamp': time.time(),
            'message': f"Deteksi {label} pada {datetime.datetime.now().strftime('%H:%M:%S')}"
        }

        # 2. Trigger Recording (Jika belum merekam)
        # Cek state recording global sederhana agar tidak tumpang tindih
        if not CAMERA_STATES.get(self.session_key, {}).get('is_recording'):
            record_thread = threading.Thread(
                target=record_stream, 
                args=(self.ip, self.user, self.password, 10, self.session_key)
            )
            record_thread.start()

def record_stream(ip2, user2, password2, duration, session_key):
    """Merekam stream RTSP selama durasi tertentu (detik)"""
    
    # Update state sedang merekam
    if session_key in CAMERA_STATES:
        CAMERA_STATES[session_key]['is_recording'] = True

    rtsp_url = f"rtsp://{user2}:{password2}@{ip2}:554/stream1"
    cap = cv2.VideoCapture(rtsp_url)
    
    # Setup Video Writer
    filename = f"capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    filepath = os.path.join(settings.MEDIA_ROOT, 'recordings', filename)
    
    # Pastikan folder ada
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    fps = 15 # Tapo biasanya 15fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    
    start_time = time.time()
    print(f"Start Recording: {filepath}")

    while int(time.time() - start_time) < duration:
        ret, frame = cap.read()
        if ret:
            out.write(frame)
        else:
            break
    
    cap.release()
    out.release()
    print("Recording finished.")
    
    # Reset state recording
    if session_key in CAMERA_STATES:
        CAMERA_STATES[session_key]['is_recording'] = False