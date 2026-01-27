import sys
import os
import time
import re
import logging.config
from onvif import ONVIFCamera
from zeep import Client
from zeep.wsse.username import UsernameToken


# Ini akan mencetak SEMUA data yang dikirim Tapo ke Dashboard (Terminal)

logging.basicConfig(level=logging.INFO)
logging.getLogger('zeep.transports').setLevel(logging.DEBUG) # <--- Level DEBUG untuk lihat XML

# --- KONFIGURASI ---
IP = "192.168.0.109"
PORT = 2020
USER = "nayakapratama"
PASS = "nayakapratama" 

def get_tapo_proof_data():
    print("\n=== TAPO DATA PROOF COLLECTOR (V11) ===")
    print("Tujuan: Menangkap raw XML yang dikirim Tapo sebagai bukti transfer data.\n")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    wsdl_path = os.path.join(current_dir, 'wsdl')
    
    if not os.path.exists(wsdl_path):
        print(f"[ERROR] Folder wsdl tidak ditemukan!")
        return

    try:
        # 1. KONEKSI AWAL
        print(f"[INFO] Connecting to {IP}...")
        cam = ONVIFCamera(IP, PORT, USER, PASS, wsdl_dir=wsdl_path)
        
        # 2. SUBSCRIBE (Tanpa parameter aneh-aneh biar gak error)
        print("[INFO] Subscribing to Events...")
        event_service = cam.create_events_service()
        subscription_response = event_service.CreatePullPointSubscription()
        
        # 3. PERBAIKI ALAMAT (PORT 80 -> 2020)
        try:
            raw_url = subscription_response.SubscriptionReference.Address._value_1
        except:
            raw_url = subscription_response.SubscriptionReference.Address

        final_url = raw_url
        if f":{PORT}/" not in raw_url:
             final_url = re.sub(r':\d+/', f':{PORT}/', raw_url)
             print(f"[FIX] URL Endpoint Data: {final_url}")

        # 4. BUAT KONEKSI SECURE (WSSE)
        print("[INFO] Establishing Secure Tunnel (WSSE)...")
        events_wsdl_file = os.path.join(wsdl_path, 'events.wsdl')
        binding_name = '{http://www.onvif.org/ver10/events/wsdl}PullPointSubscriptionBinding'
        
        token = UsernameToken(USER, PASS, use_digest=True)
        pullpoint_client = Client(wsdl=events_wsdl_file, transport=cam.transport, wsse=token)
        pullpoint = pullpoint_client.create_service(binding_name, final_url)

        print("\n" + "="*50)
        print("LISTENER AKTIF. MENUNGGU DATA XML DARI TAPO...")
        print("Gerakkan tangan di depan kamera sekarang!")
        print("Perhatikan teks XML yang muncul di bawah (DEBUG:zeep.transports...)")
        print("="*50 + "\n")

        # 5. LOOPING PENGAMBILAN BUKTI
        while True:
            try:
                # Hasilnya akan otomatis di-print oleh logging DEBUG di atas
                pullpoint.PullMessages(Timeout='PT5S', MessageLimit=10)
                
            except Exception as e:
                pass

    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")

if __name__ == "__main__":
    get_tapo_proof_data()