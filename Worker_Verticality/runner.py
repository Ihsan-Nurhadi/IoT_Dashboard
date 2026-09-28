"""
Unified ESP32-Vertical Simulator Runner with Dynamic Admin Sync & Auto-Recovery
Menjalankan simulasi data IoT ESP32 Verticality ke server MQTT (EMQX / NMS).
Fitur Unggulan:
- Terintegrasi langsung dengan Dashboard Admin Panel (Master ON/OFF & Per-Site Toggle)
- Dynamic Hot-Reload: Penambahan/penghapusan/pemadaman site berlaku realtime tanpa restart container
- Zero State Nyangkut: Otomatis membersihkan retained message ("") di EMQX saat site atau master simulator dimatikan
- Thread Watchdog / Supervisor: Memantau dan me-restart worker yang crash
- Heartbeat file (/tmp/worker_alive) untuk Docker Healthcheck
- Standalone / Offline Fallback: Otomatis membaca devices.json jika backend sedang offline
"""

import json
import math
import os
import random
import signal
import sys
import threading
import time
import urllib.request
from datetime import datetime

import paho.mqtt.client as mqtt

# ==============================================================================
# GLOBAL CONFIGURATION FROM ENVIRONMENT
# ==============================================================================
BROKER_HOST       = os.getenv("BROKER_HOST", "emqx.nayakanms.com")
BROKER_PORT       = int(os.getenv("BROKER_PORT", "1884"))
MQTT_USER         = os.getenv("MQTT_USER", "nyk_ws")
MQTT_PASS         = os.getenv("MQTT_PASS", "ws")

PROJECT           = os.getenv("PROJECT", "vertical")
FW_VERSION        = os.getenv("FW_VERSION", "0.4.0")
LOCAL_IP          = os.getenv("LOCAL_IP", "192.168.1.150")

TOWER_HEIGHT_MM   = int(os.getenv("TOWER_HEIGHT_MM", "42000"))
TILT_TOL_DEG      = float(os.getenv("TILT_TOL_DEG", "0.286"))
SWAY_TOL_MM       = float(os.getenv("SWAY_TOL_MM", "210.0"))
INTERVAL_SEC      = float(os.getenv("INTERVAL_SEC", "5"))
HEARTBEAT_SEC     = float(os.getenv("HEARTBEAT_SEC", "60"))

BACKEND_SYNC_URL  = os.getenv("BACKEND_SYNC_URL", "http://backend:8000/api/verticality/simulator-sync/")
SYNC_INTERVAL_SEC = float(os.getenv("SYNC_INTERVAL_SEC", "5.0"))

DEVICES_FILE      = os.getenv("DEVICES_FILE", os.path.join(os.path.dirname(__file__), "devices.json"))
HEALTH_FILE       = os.getenv("HEALTH_FILE", "/tmp/worker_alive")


def touch_health_file():
    """Update file heartbeat untuk Docker Healthcheck."""
    try:
        os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception:
        pass


def format_uptime(seconds: int) -> str:
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    secs = seconds % 60
    return f"{days}d {hours}h {minutes}m {secs}s"


class VerticalityWorker:
    """Class simulator untuk satu device ESP32 Verticality dengan auto-recovery & clean purge."""

    def __init__(self, chip_id: str, mac_address: str, tower_height: int = TOWER_HEIGHT_MM):
        self.chip_id = chip_id
        self.mac_address = mac_address
        self.tower_height = tower_height or TOWER_HEIGHT_MM
        self.start_time = time.time()
        self.stop_event = threading.Event()
        self.is_connected = False
        self.last_successful_publish = time.time()
        self.client = None

        # Format Topik: nms/<client_id>/vertical/<leaf>
        self.topic_prefix = f"nms/{self.chip_id}/{PROJECT}"
        self.topic_info = f"{self.topic_prefix}/info"
        self.topic_heartbeat = f"{self.topic_prefix}/heartbeat"
        self.topic_tilt = f"{self.topic_prefix}/tilt"
        self.topic_wind = f"{self.topic_prefix}/wind"
        self.topic_config = f"{self.topic_prefix}/config"
        self.topic_audit = f"{self.topic_prefix}/audit"

    def log(self, message: str):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{self.chip_id}] {message}", flush=True)

    def _init_client(self):
        """Membuat instance MQTT Client baru dengan konfigurasi socket bersih."""
        try:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass
        except Exception:
            pass

        self.is_connected = False

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.chip_id)
        except AttributeError:
            client = mqtt.Client(client_id=self.chip_id)

        client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        try:
            client.reconnect_delay_set(min_delay=1, max_delay=15)
        except Exception:
            pass

        self.client = client

    def create_info_payload(self) -> dict:
        return {
            "info": {
                "fw": FW_VERSION,
                "project": PROJECT,
                "build": datetime.now().strftime("%b %d %Y %H:%M:%S"),
                "mac": self.mac_address,
                "client_id": self.chip_id
            }
        }

    def create_heartbeat_payload(self) -> dict:
        uptime_sec = int(time.time() - self.start_time)
        return {
            "heartbeat": {
                "IP": LOCAL_IP,
                "Uptime": format_uptime(uptime_sec),
                "fw": FW_VERSION
            }
        }

    def create_tilt_payload(self) -> dict:
        tilt_x = round(random.uniform(-0.08, 0.08), 3)
        tilt_y = round(random.uniform(-0.08, 0.08), 3)
        tilt = round(math.sqrt(tilt_x**2 + tilt_y**2), 3)

        tilt_rad = math.radians(tilt)
        sway = round(self.tower_height * math.tan(tilt_rad), 1)

        status = "TOLERANCE" if (tilt <= TILT_TOL_DEG and sway <= SWAY_TOL_MM) else "INTOLERANCE"

        return {
            "ip": LOCAL_IP,
            "ts": int(time.time() * 1000) % 100000000,
            "tilt_x": tilt_x,
            "tilt_y": tilt_y,
            "tilt": tilt,
            "tilt_tol": TILT_TOL_DEG,
            "sway": sway,
            "sway_tol": SWAY_TOL_MM,
            "status": status
        }

    def create_wind_payload(self) -> dict:
        speed_ms = round(random.uniform(1.0, 5.5), 1)
        speed_kn = round(speed_ms * 1.94384, 2)

        return {
            "ip": LOCAL_IP,
            "ts": int(time.time() * 1000) % 100000000,
            "wind_speed_ms": speed_ms,
            "wind_speed_kn": speed_kn
        }

    def on_connect(self, client, userdata, flags, rc, properties=None):
        rc_code = getattr(rc, "value", rc)
        if rc_code == 0:
            self.is_connected = True
            self.last_successful_publish = time.time()
            self.log(f"Berhasil terhubung ke broker {BROKER_HOST}:{BROKER_PORT} (MAC: {self.mac_address})")

            # 1. Publish Info Retained
            try:
                info_payload = json.dumps(self.create_info_payload())
                client.publish(self.topic_info, info_payload, retain=True)
                self.log(f"PUB info (retained): {info_payload}")
            except Exception as e:
                self.log(f"Gagal publish info: {e}")

            # 2. Subscribe ke config & audit
            try:
                client.subscribe(self.topic_config)
                client.subscribe(self.topic_audit)
                self.log(f"Subscribed: {self.topic_config} & {self.topic_audit}")
            except Exception as e:
                self.log(f"Gagal subscribe: {e}")

            # 3. Publish Heartbeat awal
            try:
                hb_payload = json.dumps(self.create_heartbeat_payload())
                client.publish(self.topic_heartbeat, hb_payload)
                self.log(f"PUB heartbeat awal: {hb_payload}")
            except Exception as e:
                self.log(f"Gagal publish heartbeat awal: {e}")
        else:
            self.is_connected = False
            self.log(f"Gagal connect ke broker, return code: {rc}")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8', errors='ignore')
        self.log(f"PESAN MASUK di {msg.topic}: {payload}")

    def on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        rc_code = getattr(rc, "value", rc)
        if rc_code != 0 and not self.stop_event.is_set():
            self.log(f"Koneksi terputus tak terduga (rc={rc_code}). Paho auto-reconnect aktif...")
        else:
            self.log("Terputus dari MQTT broker secara normal.")

    def _publish_safe(self, topic: str, payload: dict, label: str) -> bool:
        """Kirim pesan dengan verifikasi status return code paho-mqtt."""
        if not self.is_connected or self.stop_event.is_set():
            return False

        try:
            payload_str = json.dumps(payload)
            pub_res = self.client.publish(topic, payload_str, qos=0)
            if pub_res.rc == mqtt.MQTT_ERR_SUCCESS:
                self.log(f"[{label}] -> {payload}")
                self.last_successful_publish = time.time()
                touch_health_file()
                return True
            else:
                self.is_connected = False
                self.log(f"[WARN] Publish {label} gagal (rc={pub_res.rc} - Disconnected). Menunggu reconnect...")
                return False
        except Exception as e:
            self.is_connected = False
            self.log(f"[ERROR] Exception saat publish {label}: {e}")
            return False

    def run(self):
        """Loop eksekusi utama dengan auto-recovery tanpa batas."""
        time.sleep(random.uniform(0.1, 1.5))

        while not self.stop_event.is_set():
            try:
                self._init_client()
                self._connect_and_loop()
            except Exception as e:
                if not self.stop_event.is_set():
                    self.log(f"Exception di worker loop: {e}. Menginisialisasi ulang dalam 5 detik...")
                    self.stop_event.wait(5.0)

    def _connect_and_loop(self):
        """Koneksi ke broker dan loop pengiriman data."""
        self.log(f"Mencoba menghubungkan ke {BROKER_HOST}:{BROKER_PORT}...")
        
        retry_delay = 3.0
        while not self.stop_event.is_set():
            try:
                self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
                self.client.loop_start()
                break
            except Exception as e:
                if self.stop_event.is_set():
                    return
                self.log(f"Koneksi awal gagal ({e}). Retry dalam {int(retry_delay)}s...")
                self.stop_event.wait(retry_delay)
                retry_delay = min(retry_delay * 1.5, 20.0)

        if self.stop_event.is_set():
            return

        last_hb_time = time.time()

        while not self.stop_event.is_set():
            now = time.time()

            # Deteksi koneksi macet (>20s tanpa publish)
            if not self.is_connected and (now - self.last_successful_publish > 20.0):
                self.log("Koneksi terputus/stale socket terdeteksi (>20s). Re-creating clean MQTT client...")
                break

            # Kirim Heartbeat berkala
            if now - last_hb_time >= HEARTBEAT_SEC:
                last_hb_time = now
                hb = self.create_heartbeat_payload()
                self._publish_safe(self.topic_heartbeat, hb, "HEARTBEAT")

            # Kirim Data Tilt
            tilt_data = self.create_tilt_payload()
            self._publish_safe(self.topic_tilt, tilt_data, "TILT")

            # Kirim Data Wind
            wind_data = self.create_wind_payload()
            self._publish_safe(self.topic_wind, wind_data, "WIND")

            # Sleep responsif terhadap stop_event
            slept = 0.0
            while slept < INTERVAL_SEC and not self.stop_event.is_set():
                time.sleep(0.5)
                slept += 0.5

    def stop(self, purge_retain: bool = True):
        """Hentikan worker secara bersih dan bersihkan retained message di broker."""
        self.stop_event.set()
        try:
            if self.client:
                # 1. Bersihkan retained message agar status tidak nyangkut online di broker
                if purge_retain and self.is_connected:
                    try:
                        self.log("Membersihkan cache retained info di broker EMQX...")
                        self.client.publish(self.topic_info, "", qos=1, retain=True)
                        self.client.publish(self.topic_heartbeat, "", qos=1, retain=True)
                        time.sleep(0.3)
                    except Exception:
                        pass
                
                # 2. Kirim DISCONNECT paket MQTT resmi
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass


def fetch_backend_sync() -> dict | None:
    """Mengambil status master dan daftar site yang aktif dari Backend API."""
    try:
        req = urllib.request.Request(
            BACKEND_SYNC_URL,
            headers={"User-Agent": "VerticalitySimulator/2.0"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                return data
    except Exception:
        pass
    return None


def load_fallback_devices() -> list:
    """Fallback ke devices.json jika backend belum siap saat pertama start."""
    env_chip = os.getenv("CHIP_ID")
    env_mac = os.getenv("MAC_ADDRESS")

    if env_chip and env_mac:
        return [{"chip_id": env_chip, "mac_address": env_mac, "tower_height": TOWER_HEIGHT_MM}]

    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                all_devs = json.load(f)
                return [
                    {
                        "chip_id": d.get("chip_id"),
                        "mac_address": d.get("mac_address", "00:00:00:00:00:00"),
                        "tower_height": d.get("tower_height", TOWER_HEIGHT_MM)
                    }
                    for d in all_devs if d.get("chip_id")
                ]
        except Exception:
            pass
    return []


def main():
    print("=" * 70, flush=True)
    print("   UNIFIED ESP32 VERTICALITY SIMULATOR (DYNAMIC ADMIN SYNC)", flush=True)
    print("=" * 70, flush=True)
    print(f"Broker Target   : {BROKER_HOST}:{BROKER_PORT}", flush=True)
    print(f"MQTT User       : {MQTT_USER}", flush=True)
    print(f"Backend Sync URL: {BACKEND_SYNC_URL}", flush=True)
    print(f"Sensor Interval : {INTERVAL_SEC}s | Heartbeat Interval : {HEARTBEAT_SEC}s", flush=True)
    print("=" * 70, flush=True)

    active_workers = {}  # chip_id -> {"worker": VerticalityWorker, "thread": Thread}
    stop_event = threading.Event()
    last_backend_online = False

    def handle_signal(sig, frame):
        print(f"\n[SUPERVISOR] Menerima sinyal stop ({sig}). Menghentikan seluruh worker...", flush=True)
        stop_event.set()
        for chip, item in list(active_workers.items()):
            item["worker"].stop(purge_retain=True)
        active_workers.clear()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("[SUPERVISOR] Memulai sinkronisasi awal dengan Backend API...", flush=True)

    try:
        while not stop_event.is_set():
            touch_health_file()

            # 1. Coba sinkronisasi dengan Backend API
            sync_data = fetch_backend_sync()

            if sync_data is not None:
                if not last_backend_online:
                    print("[SUPERVISOR] ✓ Terhubung dengan Backend API. Menggunakan konfigurasi dinamis Admin Panel.", flush=True)
                    last_backend_online = True

                is_master = sync_data.get("is_master_enabled", True)
                devices_list = sync_data.get("devices", []) if is_master else []
                target_map = {d["chip_id"]: d for d in devices_list if d.get("chip_id")}

                # A. Jika Master Switch dimatikan atau target_map kosong:
                if not is_master:
                    if len(active_workers) > 0:
                        print(f"[SUPERVISOR] Master Switch bernilai OFF. Menghentikan {len(active_workers)} worker dan membersihkan cache broker...", flush=True)
                        for chip, item in list(active_workers.items()):
                            item["worker"].stop(purge_retain=True)
                        active_workers.clear()
                        print("[SUPERVISOR] Seluruh worker telah dinonaktifkan bersih (0 state nyangkut).", flush=True)

                else:
                    # B. Hentikan worker yang sudah dinonaktifkan per-site (Mode Real aktif / Site dihapus)
                    to_remove = set(active_workers.keys()) - set(target_map.keys())
                    for chip in to_remove:
                        print(f"[SUPERVISOR] Site {chip} dinonaktifkan dari Admin Panel. Menghentikan worker & membersihkan retain...", flush=True)
                        active_workers[chip]["worker"].stop(purge_retain=True)
                        del active_workers[chip]

                    # C. Jalankan worker baru yang ditambahkan di Admin Panel
                    to_add = set(target_map.keys()) - set(active_workers.keys())
                    for chip in to_add:
                        d = target_map[chip]
                        mac = d.get("mac_address", "00:00:00:00:00:00")
                        height = d.get("tower_height", TOWER_HEIGHT_MM)
                        print(f"[SUPERVISOR] Mengaktifkan simulator untuk site {chip} ({mac})...", flush=True)
                        w = VerticalityWorker(chip, mac, height)
                        t = threading.Thread(target=w.run, name=f"Thread-{chip}", daemon=True)
                        t.start()
                        active_workers[chip] = {"worker": w, "thread": t}

            else:
                # Backend offline atau mode standalone awal
                if last_backend_online:
                    print("[SUPERVISOR WARN] Kehilangan koneksi ke Backend API. Menjaga status worker terakhir.", flush=True)
                    last_backend_online = False

                if len(active_workers) == 0:
                    fallback_devs = load_fallback_devices()
                    print(f"[SUPERVISOR] Menggunakan fallback lokal ({len(fallback_devs)} devices)...", flush=True)
                    for d in fallback_devs:
                        chip = d["chip_id"]
                        mac = d.get("mac_address", "00:00:00:00:00:00")
                        height = d.get("tower_height", TOWER_HEIGHT_MM)
                        w = VerticalityWorker(chip, mac, height)
                        t = threading.Thread(target=w.run, name=f"Thread-{chip}", daemon=True)
                        t.start()
                        active_workers[chip] = {"worker": w, "thread": t}

            # 2. Watchdog: Cek kesehatan thread yang sedang aktif
            for chip, item in list(active_workers.items()):
                t = item["thread"]
                w = item["worker"]
                if not t.is_alive() and not stop_event.is_set():
                    print(f"[WATCHDOG ALERT] Thread {chip} mati secara tak terduga! Auto-restarting thread...", flush=True)
                    new_t = threading.Thread(target=w.run, name=f"Thread-{chip}-revived", daemon=True)
                    new_t.start()
                    active_workers[chip]["thread"] = new_t

            # Tunggu interval sinkronisasi
            slept = 0.0
            while slept < SYNC_INTERVAL_SEC and not stop_event.is_set():
                time.sleep(0.5)
                slept += 0.5

    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)

    print("[SUPERVISOR] Menunggu seluruh worker selesai...", flush=True)
    for chip, item in active_workers.items():
        item["thread"].join(timeout=2.0)

    try:
        if os.path.exists(HEALTH_FILE):
            os.remove(HEALTH_FILE)
    except Exception:
        pass

    print("[SUPERVISOR] Seluruh worker telah berhenti total. Keluar.", flush=True)


if __name__ == "__main__":
    main()
