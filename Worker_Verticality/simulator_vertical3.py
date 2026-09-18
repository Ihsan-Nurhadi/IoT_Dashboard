"""
Script Simulator Data Dummy ESP32-Vertical
Mensimulasikan pengiriman data IoT ke server (EMQX / NMS) tanpa ESP32 fisik.
"""

import json
import math
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# ==============================================================================
# KONFIGURASI SESUAI FIRMWARE & REQUEST
# ==============================================================================
BROKER_HOST = "emqx.nayakanms.com"
BROKER_PORT = 1884  # Default di config.h adalah 1884 (ganti ke 1883 jika perlu)
MQTT_USER   = "nyk_ws"
MQTT_PASS   = "ws"

CHIP_ID     = "E32_VER_SMU84"
MAC_ADDRESS = "71:0D:4E:CA:62:6A"
PROJECT     = "vertical"
FW_VERSION  = "0.4.0"
LOCAL_IP    = "192.168.1.150"

# Parameter Tower & Batas Toleransi (sesuai config.h)
TOWER_HEIGHT_MM = 42000    # 42 meter
TILT_TOL_DEG    = 0.286
SWAY_TOL_MM     = 210.0
INTERVAL_SEC    = 5        # Kirim data sensor setiap 5 detik
HEARTBEAT_SEC   = 60       # Kirim heartbeat setiap 60 detik (default ESP32 = 300s)

# Format Topik: nms/<client_id>/vertical/<leaf>
TOPIC_PREFIX = f"nms/{CHIP_ID}/{PROJECT}"
TOPIC_INFO      = f"{TOPIC_PREFIX}/info"
TOPIC_HEARTBEAT = f"{TOPIC_PREFIX}/heartbeat"
TOPIC_TILT      = f"{TOPIC_PREFIX}/tilt"
TOPIC_WIND      = f"{TOPIC_PREFIX}/wind"
TOPIC_CONFIG    = f"{TOPIC_PREFIX}/config"
TOPIC_AUDIT     = f"{TOPIC_PREFIX}/audit"

start_time = time.time()


def format_uptime(seconds: int) -> str:
    days = seconds // 86400
    seconds %= 86400
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    secs = seconds % 60
    return f"{days}d {hours}h {minutes}m {secs}s"


# ==============================================================================
# PEMBUATAN PAYLOAD DATA SENSOR & STATUS
# ==============================================================================
def create_info_payload() -> dict:
    """Payload retained saat pertama kali terkoneksi (registrasi device)."""
    return {
        "info": {
            "fw": FW_VERSION,
            "project": PROJECT,
            "build": datetime.now().strftime("%b %d %Y %H:%M:%S"),
            "mac": MAC_ADDRESS,
            "client_id": CHIP_ID
        }
    }


def create_heartbeat_payload() -> dict:
    """Payload heartbeat untuk memastikan status device online."""
    uptime_sec = int(time.time() - start_time)
    return {
        "heartbeat": {
            "IP": LOCAL_IP,
            "Uptime": format_uptime(uptime_sec),
            "fw": FW_VERSION
        }
    }


def create_tilt_payload() -> dict:
    """Payload data tilt (inklinometer) & sway tower."""
    # Data dummy dengan sedikit fluktuasi acak realistis di bawah batas toleransi
    tilt_x = round(random.uniform(-0.08, 0.08), 3)
    tilt_y = round(random.uniform(-0.08, 0.08), 3)
    tilt = round(math.sqrt(tilt_x**2 + tilt_y**2), 3)

    # Menghitung goyangan (sway dalam mm) berdasarkan tinggi tower
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


def create_wind_payload() -> dict:
    """Payload kecepatan angin (anemometer)."""
    speed_ms = round(random.uniform(1.0, 5.5), 1)
    speed_kn = round(speed_ms * 1.94384, 2)

    return {
        "ip": LOCAL_IP,
        "ts": int(time.time() * 1000) % 100000000,
        "wind_speed_ms": speed_ms,
        "wind_speed_kn": speed_kn
    }


# ==============================================================================
# MQTT CALLBACKS
# ==============================================================================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"\n[MQTT] Berhasil terhubung ke broker {BROKER_HOST}:{BROKER_PORT}")
        print(f"[MQTT] Client ID : {CHIP_ID}")
        print(f"[MQTT] MAC       : {MAC_ADDRESS}")

        # 1. Publish Info Retained (Registrasi identitas device)
        info_payload = json.dumps(create_info_payload())
        client.publish(TOPIC_INFO, info_payload, retain=True)
        print(f"[MQTT -> PUB] {TOPIC_INFO} (retained): {info_payload}")

        # 2. Subscribe ke remote config & audit
        client.subscribe(TOPIC_CONFIG)
        client.subscribe(TOPIC_AUDIT)
        print(f"[MQTT -> SUB] Subscribed ke {TOPIC_CONFIG} & {TOPIC_AUDIT}")

        # 3. Publish Heartbeat awal
        hb_payload = json.dumps(create_heartbeat_payload())
        client.publish(TOPIC_HEARTBEAT, hb_payload)
        print(f"[MQTT -> PUB] {TOPIC_HEARTBEAT}: {hb_payload}\n")
    else:
        print(f"[MQTT ERROR] Gagal connect, return code: {rc}")


def on_message(client, userdata, msg):
    print(f"\n[MQTT <- PESAN MASUK] Topik: {msg.topic}")
    print(f"[MQTT <- DATA] {msg.payload.decode('utf-8', errors='ignore')}")


# ==============================================================================
# MAIN LOOP
# ==============================================================================
def main():
    print("=" * 65)
    print("      SIMULATOR ESP32 VERTICAL (INJECT DUMMY DATA PYTHON)")
    print("=" * 65)

    # Inisialisasi client MQTT (kompatibel paho-mqtt v2.x dan v1.x)
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CHIP_ID)
    except AttributeError:
        client = mqtt.Client(client_id=CHIP_ID)

    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Menghubungkan ke {BROKER_HOST}:{BROKER_PORT}...")
    try:
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    except Exception as e:
        print(f"Error koneksi: {e}")
        return

    client.loop_start()

    last_hb_time = time.time()

    try:
        while True:
            now = time.time()

            # Kirim Heartbeat berkala
            if now - last_hb_time >= HEARTBEAT_SEC:
                last_hb_time = now
                hb = create_heartbeat_payload()
                client.publish(TOPIC_HEARTBEAT, json.dumps(hb))
                print(f"[HEARTBEAT] {TOPIC_HEARTBEAT} -> {hb}")

            # Kirim Data Tilt
            tilt_data = create_tilt_payload()
            client.publish(TOPIC_TILT, json.dumps(tilt_data))
            print(f"[TILT] {TOPIC_TILT} -> {tilt_data}")

            # Kirim Data Wind
            wind_data = create_wind_payload()
            client.publish(TOPIC_WIND, json.dumps(wind_data))
            print(f"[WIND] {TOPIC_WIND} -> {wind_data}")

            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\nSimulator dihentikan oleh user.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Terputus dari MQTT broker.")


if __name__ == "__main__":
    main()
