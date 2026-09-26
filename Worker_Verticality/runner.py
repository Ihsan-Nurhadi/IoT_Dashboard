"""
Unified ESP32-Vertical Simulator Runner with Auto-Reconnect & Supervisor
Menjalankan simulasi data IoT ESP32 Verticality ke server MQTT (EMQX / NMS).
Dilengkapi fitur:
- Auto-reconnect jika koneksi broker MQTT terputus (Paho loop & manual fallback)
- Watchdog / Supervisor thread yang otomatis me-restart worker jika thread mati
- Heartbeat file (/tmp/worker_alive) untuk Docker Healthcheck
- Graceful shutdown saat menerima sinyal SIGINT/SIGTERM
"""

import json
import math
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt

# ==============================================================================
# GLOBAL CONFIGURATION FROM ENVIRONMENT
# ==============================================================================
BROKER_HOST     = os.getenv("BROKER_HOST", "emqx.nayakanms.com")
BROKER_PORT     = int(os.getenv("BROKER_PORT", "1884"))
MQTT_USER       = os.getenv("MQTT_USER", "nyk_ws")
MQTT_PASS       = os.getenv("MQTT_PASS", "ws")

PROJECT         = os.getenv("PROJECT", "vertical")
FW_VERSION      = os.getenv("FW_VERSION", "0.4.0")
LOCAL_IP        = os.getenv("LOCAL_IP", "192.168.1.150")

TOWER_HEIGHT_MM = int(os.getenv("TOWER_HEIGHT_MM", "42000"))
TILT_TOL_DEG    = float(os.getenv("TILT_TOL_DEG", "0.286"))
SWAY_TOL_MM     = float(os.getenv("SWAY_TOL_MM", "210.0"))
INTERVAL_SEC    = float(os.getenv("INTERVAL_SEC", "5"))
HEARTBEAT_SEC   = float(os.getenv("HEARTBEAT_SEC", "60"))

DEVICES_FILE    = os.getenv("DEVICES_FILE", os.path.join(os.path.dirname(__file__), "devices.json"))
HEALTH_FILE     = os.getenv("HEALTH_FILE", "/tmp/worker_alive")


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
    """Class simulator untuk satu device ESP32 Verticality dengan auto-recovery."""

    def __init__(self, chip_id: str, mac_address: str):
        self.chip_id = chip_id
        self.mac_address = mac_address
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
        """Membuat instance MQTT Client baru dengan konfigurasi reconnect otomatis."""
        try:
            if self.client:
                try:
                    self.client.loop_stop()
                    self.client.disconnect()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.chip_id)
        except AttributeError:
            client = mqtt.Client(client_id=self.chip_id)

        client.username_pw_set(MQTT_USER, MQTT_PASS)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_disconnect = self.on_disconnect

        # Set reconnect delay agresif jika koneksi socket terputus
        try:
            client.reconnect_delay_set(min_delay=1, max_delay=30)
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
        sway = round(TOWER_HEIGHT_MM * math.tan(tilt_rad), 1)

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
        if rc_code != 0:
            self.log(f"Koneksi terputus tak terduga (rc={rc}). Paho auto-reconnect aktif...")
        else:
            self.log("Terputus dari MQTT broker secara normal.")

    def run(self):
        """Loop eksekusi utama dengan auto-recovery tanpa batas."""
        # Random jitter saat start agar 11 device tidak connect serempak
        time.sleep(random.uniform(0.1, 2.0))

        while not self.stop_event.is_set():
            try:
                self._init_client()
                self._connect_and_loop()
            except Exception as e:
                self.log(f"Exception di worker loop: {e}. Melakukan reconnect dalam 5 detik...")
                self.stop_event.wait(5.0)

    def _connect_and_loop(self):
        """Koneksi ke broker dan loop pengiriman data."""
        self.log(f"Mencoba menghubungkan ke {BROKER_HOST}:{BROKER_PORT}...")
        
        # Loop percobaan connect sampai berhasil atau diminta stop
        retry_delay = 3.0
        while not self.stop_event.is_set():
            try:
                self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
                self.client.loop_start()
                break
            except Exception as e:
                self.log(f"Koneksi gagal ({e}). Retry dalam {int(retry_delay)}s...")
                self.stop_event.wait(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30.0)

        if self.stop_event.is_set():
            return

        last_hb_time = time.time()

        # Loop pengiriman sensor dan heartbeat
        while not self.stop_event.is_set():
            now = time.time()

            # Jika koneksi macet/tidak publish lebih dari 90 detik, trigger reconnect paksa
            if now - self.last_successful_publish > 120.0 and not self.is_connected:
                self.log("Koneksi macet terdeteksi (>120s tanpa publish). Memaksa reconnect...")
                try:
                    self.client.reconnect()
                except Exception as e:
                    self.log(f"Gagal force reconnect: {e}. Menginisialisasi ulang client...")
                    break  # Keluar ke _init_client() di run()

            # Kirim Heartbeat berkala
            if now - last_hb_time >= HEARTBEAT_SEC:
                last_hb_time = now
                hb = self.create_heartbeat_payload()
                try:
                    self.client.publish(self.topic_heartbeat, json.dumps(hb))
                    self.log(f"[HEARTBEAT] -> {hb}")
                    self.last_successful_publish = now
                    touch_health_file()
                except Exception as e:
                    self.log(f"Error kirim heartbeat: {e}")

            # Kirim Data Tilt
            tilt_data = self.create_tilt_payload()
            try:
                self.client.publish(self.topic_tilt, json.dumps(tilt_data))
                self.log(f"[TILT] -> {tilt_data}")
                self.last_successful_publish = now
                touch_health_file()
            except Exception as e:
                self.log(f"Error kirim tilt: {e}")

            # Kirim Data Wind
            wind_data = self.create_wind_payload()
            try:
                self.client.publish(self.topic_wind, json.dumps(wind_data))
                self.log(f"[WIND] -> {wind_data}")
                self.last_successful_publish = now
                touch_health_file()
            except Exception as e:
                self.log(f"Error kirim wind: {e}")

            # Sleep responsif terhadap stop_event
            slept = 0.0
            while slept < INTERVAL_SEC and not self.stop_event.is_set():
                time.sleep(0.5)
                slept += 0.5

    def stop(self):
        """Hentikan worker secara bersih."""
        self.stop_event.set()
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass


def load_devices() -> list:
    """Menentukan daftar device yang akan dijalankan."""
    env_chip = os.getenv("CHIP_ID")
    env_mac = os.getenv("MAC_ADDRESS")

    if env_chip and env_mac:
        print(f"[RUNNER] Mode Single Device via ENV: {env_chip} ({env_mac})", flush=True)
        return [{"chip_id": env_chip, "mac_address": env_mac}]

    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, "r", encoding="utf-8") as f:
            all_devices = json.load(f)
    else:
        print(f"[RUNNER ERROR] File devices.json tidak ditemukan di {DEVICES_FILE}!", flush=True)
        return []

    target_chips_env = os.getenv("TARGET_CHIPS")
    if target_chips_env:
        targets = [t.strip() for t in target_chips_env.split(",") if t.strip()]
        filtered = [d for d in all_devices if d.get("chip_id") in targets]
        print(f"[RUNNER] Filter {len(filtered)}/{len(all_devices)} devices sesuai TARGET_CHIPS: {targets}", flush=True)
        return filtered

    print(f"[RUNNER] Mode All Devices: Memuat seluruh {len(all_devices)} devices dari devices.json", flush=True)
    return all_devices


def main():
    print("=" * 70, flush=True)
    print("   UNIFIED ESP32 VERTICALITY SIMULATOR (AUTO-RECOVERY & SUPERVISOR)", flush=True)
    print("=" * 70, flush=True)
    print(f"Broker Target   : {BROKER_HOST}:{BROKER_PORT}", flush=True)
    print(f"MQTT User       : {MQTT_USER}", flush=True)
    print(f"Sensor Interval : {INTERVAL_SEC}s | Heartbeat Interval : {HEARTBEAT_SEC}s", flush=True)
    print("=" * 70, flush=True)

    devices = load_devices()
    if not devices:
        print("[RUNNER ERROR] Tidak ada device yang dimuat. Keluar.", flush=True)
        sys.exit(1)

    workers = []
    threads = []
    stop_event = threading.Event()

    for d in devices:
        chip = d.get("chip_id")
        mac = d.get("mac_address")
        if not chip or not mac:
            continue
        worker = VerticalityWorker(chip, mac)
        t = threading.Thread(target=worker.run, name=f"Thread-{chip}", daemon=True)
        workers.append(worker)
        threads.append(t)

    def handle_signal(sig, frame):
        print(f"\n[SUPERVISOR] Menerima sinyal stop ({sig}). Menghentikan seluruh worker...", flush=True)
        stop_event.set()
        for w in workers:
            w.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Jalankan semua thread worker
    for t in threads:
        t.start()

    print(f"[SUPERVISOR] Berhasil menjalankan {len(threads)} worker thread. Watchdog aktif.", flush=True)
    touch_health_file()

    # ==========================================================================
    # SUPERVISOR / WATCHDOG LOOP
    # Memeriksa kesehatan setiap thread berkala dan otomatis me-restart jika mati
    # ==========================================================================
    try:
        while not stop_event.is_set():
            time.sleep(5)
            touch_health_file()

            if stop_event.is_set():
                break

            # Periksa setiap worker thread
            for i, (worker, t) in enumerate(zip(workers, threads)):
                if not t.is_alive() and not stop_event.is_set():
                    print(
                        f"[SUPERVISOR ALERT] Thread worker {worker.chip_id} mati! "
                        f"Menghidupkan ulang (auto-restart) thread sekarang...",
                        flush=True
                    )
                    # Buat thread baru untuk worker yang mati
                    new_t = threading.Thread(
                        target=worker.run,
                        name=f"Thread-{worker.chip_id}-restart",
                        daemon=True
                    )
                    threads[i] = new_t
                    new_t.start()
                    print(f"[SUPERVISOR] Thread worker {worker.chip_id} berhasil dihidupkan kembali.", flush=True)

    except KeyboardInterrupt:
        handle_signal(signal.SIGINT, None)

    print("[SUPERVISOR] Menunggu seluruh worker selesai...", flush=True)
    for t in threads:
        t.join(timeout=3.0)

    # Hapus file health saat shutdown bersih
    try:
        if os.path.exists(HEALTH_FILE):
            os.remove(HEALTH_FILE)
    except Exception:
        pass

    print("[SUPERVISOR] Seluruh worker telah berhenti. Keluar.", flush=True)


if __name__ == "__main__":
    main()
