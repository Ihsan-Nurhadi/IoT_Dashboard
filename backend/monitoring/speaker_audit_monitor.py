"""
Service Monitoring & Audit Perangkat Testing ESP32 Speaker (E32_IPS_7).
Menjalankan health audit berkala per 30 menit (00:00, 00:30, ...) via MQTT:
1. Mengirim payload {"heartbeat": {}} ke topik nms/E32_IPS_7/speaker/audit
2. Mendengarkan balasan dari perangkat (nms/E32_IPS_7/speaker/audit/response atau nms/E32_IPS_7/speaker/#)
3. Menilai status ALIVE (ONLINE) jika membalas, atau DEAD (OFFLINE) jika tidak ada respon hingga batas timeout
4. Mencatat hasil audit ke Google Spreadsheet (via Google Apps Script Webhook)
5. Memperbarui status di database (DeviceState) dan matriks Excel lokal per 30 menit
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import requests
import paho.mqtt.client as mqtt

# Zona waktu Indonesia Barat (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))

# ==============================================================================
# KONFIGURASI KREDENSIAL & PARAMETER PERANGKAT TESTING
# ==============================================================================
BROKER_HOST = os.getenv("SPEAKER_TEST_BROKER", "emqx.nayakanms.com")
BROKER_PORT = int(os.getenv("SPEAKER_TEST_PORT", "1884"))
MQTT_USER   = os.getenv("SPEAKER_TEST_USER", "nyk_ws")
MQTT_PASS   = os.getenv("SPEAKER_TEST_PASS", "ws")

DEVICE_ID   = os.getenv("SPEAKER_TEST_DEVICE_ID", "E32_IPS_7")
AUDIT_TOPIC = os.getenv("SPEAKER_TEST_TOPIC", f"nms/{DEVICE_ID}/speaker/audit")
DEFAULT_PAYLOAD = os.getenv("SPEAKER_TEST_PAYLOAD", '{"heartbeat": {}}')

# Webhook Google Apps Script DEDIKASI KHUSUS Audit Speaker (Terpisah dari Verticality)
SPEAKER_GSHEET_WEBHOOK_URL = os.getenv("SPEAKER_GSHEET_WEBHOOK_URL", "")

# Timeout menunggu balasan perangkat dalam detik (default: 10 detik)
AUDIT_TIMEOUT_SECONDS = float(os.getenv("SPEAKER_AUDIT_TIMEOUT_SECONDS", "10.0"))

# Cache hasil audit terakhir di memori
LAST_AUDIT_RESULT = {
    "device_id": DEVICE_ID,
    "status": "UNKNOWN",
    "last_audit_time": None,
    "response_received": False,
    "latency_seconds": None,
    "response_topic": None,
    "response_payload": None,
    "gsheet_synced": False,
}

_SCHEDULER_LOCK = threading.Lock()
_SCHEDULER_STARTED = False


# ==============================================================================
# HELPER TIME SLOTS (30 MENIT WIB)
# ==============================================================================
def get_seconds_until_next_30min() -> float:
    """
    Menghitung jumlah detik hingga slot 30 menit berikutnya (:00 atau :30 WIB).
    Menambahkan buffer 1 detik untuk menjamin sinkronisasi.
    """
    now = datetime.now(WIB)
    current_minute = now.minute
    if current_minute < 30:
        next_target = now.replace(minute=30, second=0, microsecond=0)
    else:
        next_target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    diff = (next_target - now).total_seconds()
    return max(3.0, diff + 1.0)


def get_audit_excel_path() -> str:
    """Mengembalikan path file Excel lokal untuk backup rekapan audit 30 menit."""
    try:
        from django.conf import settings
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    except Exception:
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    return os.path.join(reports_dir, 'monitoring_speaker_audit_30min.xlsx')


# ==============================================================================
# SINKRONISASI KE GOOGLE SPREADSHEET (APPS SCRIPT WEBHOOK)
# ==============================================================================
def sync_audit_to_google_sheet(audit_data: dict, webhook_url: str = "") -> bool:
    """
    Mengirimkan log audit status perangkat ke Google Spreadsheet KHUSUS SPEAKER via Webhook Google Apps Script.
    Terpisah dari spreadsheet verticality agar data audit pengujian tidak bercampur dengan data tower verticality.
    """
    url = webhook_url or os.getenv("SPEAKER_GSHEET_WEBHOOK_URL", "") or SPEAKER_GSHEET_WEBHOOK_URL
    if not url:
        print("[i] [SPEAKER AUDIT] SPEAKER_GSHEET_WEBHOOK_URL belum diset (terpisah dari verticality). Melewati sinkronisasi Google Spreadsheet.", flush=True)
        return False

    waktu_tarik = audit_data.get("timestamp_dt", datetime.now(WIB))
    date_str = waktu_tarik.strftime("%Y-%m-%d")
    slot_minute = "30" if waktu_tarik.minute >= 30 else "00"
    slot_header = f"{waktu_tarik.hour:02d}:{slot_minute}"
    timestamp_str = waktu_tarik.strftime("%Y-%m-%d %H:%M:%S WIB")

    is_online = (audit_data.get("status") == "ONLINE")

    payload = {
        "event": "SPEAKER_AUDIT",
        "date": date_str,
        "time": slot_header,
        "timestamp": timestamp_str,
        "device_id": audit_data.get("device_id", DEVICE_ID),
        "status": audit_data.get("status"),
        "is_alive": is_online,
        "latency_seconds": audit_data.get("latency_seconds"),
        "audit_topic": audit_data.get("audit_topic", AUDIT_TOPIC),
        "response_topic": audit_data.get("response_topic") or "-",
        "response_payload": audit_data.get("response_payload") or "-",
        "broker": audit_data.get("broker", f"{BROKER_HOST}:{BROKER_PORT}"),
        # Format row siap append:
        "row": [
            timestamp_str,
            audit_data.get("device_id", DEVICE_ID),
            audit_data.get("status"),
            f"{audit_data.get('latency_seconds', 0):.2f}s" if audit_data.get("latency_seconds") is not None else "-",
            audit_data.get("audit_topic", AUDIT_TOPIC),
            audit_data.get("response_topic") or "-",
            audit_data.get("response_payload") or "-"
        ]
    }

    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] Mengirim data audit ke Google Spreadsheet ({url[:45]}...)...", flush=True)

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25
            )
            if res.status_code in (200, 201):
                print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Sukses update Google Spreadsheet: {res.text[:120]}", flush=True)
                return True
            else:
                print(f"[!] Gagal update Google Sheet: HTTP {res.status_code} (Percobaan {attempt}/{max_retries})", flush=True)
                if attempt < max_retries:
                    time.sleep(3 * attempt)
        except Exception as e:
            print(f"[!] Error koneksi ke Google Apps Script: {e} (Percobaan {attempt}/{max_retries})", flush=True)
            if attempt < max_retries:
                time.sleep(3 * attempt)

    return False


# ==============================================================================
# SINKRONISASI KE FILE EXCEL LOKAL (MATRIKS 30 MENIT)
# ==============================================================================
def update_speaker_audit_excel_matrix(audit_data: dict, file_path: str = None) -> str:
    """
    Menyimpan atau memperbarui data audit perangkat ke matriks Excel horizontal per 30 menit.
    Format sheet harian (YYYY-MM-DD) dengan kolom: [Perangkat] | [00:00] | [00:30] | ... | [23:30]
    """
    if not file_path:
        file_path = get_audit_excel_path()

    waktu_tarik = audit_data.get("timestamp_dt", datetime.now(WIB))
    sheet_name = waktu_tarik.strftime("%Y-%m-%d")

    slot_minute = "30" if waktu_tarik.minute >= 30 else "00"
    slot_header = f"{waktu_tarik.hour:02d}:{slot_minute}"

    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_cell = Font(name="Calibri", size=10)
    fill_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    fill_online = PatternFill(start_color="C6F6D5", end_color="C6F6D5", fill_type="solid")
    fill_offline = PatternFill(start_color="FED7D7", end_color="FED7D7", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    if os.path.exists(file_path):
        try:
            wb = openpyxl.load_workbook(file_path)
        except Exception:
            wb = openpyxl.Workbook()
    else:
        wb = openpyxl.Workbook()

    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        if len(wb.sheetnames) == 1 and wb.sheetnames[0] == "Sheet":
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(title=sheet_name)

        # Header awal: hanya kolom identitas perangkat (tanpa kolom kosong 00:00-23:30)
        headers = ["No", "Device Name", "Device ID", "Topic Audit"]

        ws.row_dimensions[1].height = 26
        for col_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = thin_border

        # Isi row 2 untuk identitas perangkat
        ws.cell(row=2, column=1, value=1).alignment = align_center
        ws.cell(row=2, column=2, value="Testing ESP32 Speaker").alignment = align_left
        ws.cell(row=2, column=3, value=audit_data.get("device_id", DEVICE_ID)).alignment = align_left
        ws.cell(row=2, column=4, value=AUDIT_TOPIC).alignment = align_left

    # Cari apakah kolom slot waktu ini sudah ada
    target_col = None
    for col in range(5, ws.max_column + 1):
        if str(ws.cell(row=1, column=col).value).strip() == slot_header:
            target_col = col
            break

    # Jika belum ada, tambahkan kolom baru di sebelah kanan secara kronologis (D -> E -> F...)
    # tanpa membuat kolom-kolom kosong 00:00 - 15:00
    if not target_col:
        target_col = ws.max_column + 1
        h_cell = ws.cell(row=1, column=target_col, value=slot_header)
        h_cell.font = font_header
        h_cell.fill = fill_header
        h_cell.alignment = align_center
        h_cell.border = thin_border

    status_val = audit_data.get("status", "OFFLINE")
    cell = ws.cell(row=2, column=target_col, value=status_val)
    cell.font = font_bold
    cell.alignment = align_center
    cell.border = thin_border
    cell.fill = fill_online if status_val == "ONLINE" else fill_offline

    ws.column_dimensions["A"].width = 6
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 32
    for col_i in range(5, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col_i)].width = 10

    wb.save(file_path)
    return file_path


# ==============================================================================
# AUDIT RUNNER UTAMA (REQUEST - RESPONSE CHECKER)
# ==============================================================================
def run_speaker_health_audit(
    broker: str = BROKER_HOST,
    port: int = BROKER_PORT,
    user: str = MQTT_USER,
    password: str = MQTT_PASS,
    device_id: str = DEVICE_ID,
    audit_topic: str = AUDIT_TOPIC,
    payload_str: str = DEFAULT_PAYLOAD,
    timeout_sec: float = AUDIT_TIMEOUT_SECONDS,
    sync_gsheet: bool = True,
    update_excel: bool = True,
    gsheet_url: str = "",
) -> dict:
    """
    Melakukan 1 siklus audit langsung ke perangkat:
    1. Connect ke EMQX broker
    2. Subscribe ke topic response perangkat (nms/<device_id>/speaker/audit/response & nms/<device_id>/speaker/#)
    3. Publish heartbeat payload ke topic audit
    4. Tunggu balasan hingga timeout
    5. Nilai ALIVE (ONLINE) jika membalas, DEAD (OFFLINE) jika timeout
    6. Sinkronkan ke Google Sheet, Database, dan Excel lokal
    """
    global LAST_AUDIT_RESULT
    start_time = time.time()
    now_dt = datetime.now(WIB)
    timestamp_str = now_dt.strftime("%Y-%m-%d %H:%M:%S WIB")

    response_event = threading.Event()
    audit_context = {
        "received": False,
        "response_topic": None,
        "response_payload": None,
        "latency": None,
        "publish_time": None,
    }

    response_topics = [
        f"nms/{device_id}/speaker/audit/response",
        f"nms/{device_id}/speaker/heartbeat",
        f"nms/{device_id}/speaker/#",
    ]

    client_id = f"auditor_{device_id}_{int(time.time() * 1000) % 1000000}"

    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
    except AttributeError:
        client = mqtt.Client(client_id=client_id)

    client.username_pw_set(user, password)

    def on_connect(c, userdata, flags, rc, properties=None):
        reason_code = rc if isinstance(rc, int) else getattr(rc, "value", rc)
        if reason_code == 0:
            for top in response_topics:
                c.subscribe(top, qos=0)

    def on_message(c, userdata, msg):
        # 1. ABAIKAN pesan RETAIN (pesan lama yang disimpan broker saat perangkat offline/connect)
        if getattr(msg, "retain", False):
            return

        # 2. ABAIKAN pesan yang masuk sebelum request audit resmi di-publish
        publish_time = audit_context.get("publish_time")
        if publish_time is None:
            return

        # 3. ABAIKAN pesan yang kita publish sendiri ke topic audit
        if msg.topic == audit_topic:
            return

        # 4. ABAIKAN pesan info (retained atau info spek, bukan balasan heartbeat)
        if msg.topic.endswith("/info"):
            return

        try:
            payload_text = msg.payload.decode("utf-8", errors="replace").strip()
        except Exception:
            payload_text = str(msg.payload)

        # Abaikan jika isi payload adalah metadata info
        if '"info"' in payload_text and '"heartbeat"' not in payload_text:
            return

        # 5. VALIDASI: Balasan resmi audit speaker HARUS berisi {"heartbeat": {...}}
        # Contoh balasan valid: {"heartbeat":{"IP":"192.168.8.159","Uptime":"0d 1h 19m 16s","fw":"0.1.3"}}
        is_valid_heartbeat = False
        try:
            parsed = json.loads(payload_text)
            if isinstance(parsed, dict) and "heartbeat" in parsed:
                hb = parsed["heartbeat"]
                # Pastikan heartbeat bukan objek kosong {} (yang kita kirim sendiri)
                if isinstance(hb, dict) and len(hb) > 0:
                    is_valid_heartbeat = True
                elif isinstance(hb, dict):
                    # Jika objek heartbeat dikirim dari perangkat
                    is_valid_heartbeat = True
        except Exception:
            if '"heartbeat"' in payload_text and ('"IP"' in payload_text or '"Uptime"' in payload_text or '"fw"' in payload_text):
                is_valid_heartbeat = True

        if is_valid_heartbeat and f"nms/{device_id}/speaker" in msg.topic:
            audit_context["received"] = True
            audit_context["response_topic"] = msg.topic
            audit_context["response_payload"] = payload_text
            audit_context["latency"] = max(0.001, time.time() - publish_time)
            response_event.set()

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] Memulai pengecekan perangkat '{device_id}'...", flush=True)
    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] Broker: {broker}:{port} | User: {user}", flush=True)
    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] Target Topic: {audit_topic} | Payload: {payload_str}", flush=True)

    connected = False
    try:
        rc = client.connect(broker, port, keepalive=30)
        client.loop_start()
        time.sleep(1.0)  # Berikan jeda sejenak untuk koneksi & subscribe broker selesai
        connected = True

        # Catat waktu publish dan kirim payload audit ke perangkat
        audit_context["publish_time"] = time.time()
        client.publish(audit_topic, payload=payload_str, qos=0)
        print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] Payload terkirim. Menunggu balasan heartbeat (timeout {timeout_sec}s)...", flush=True)

        # Tunggu respon dari perangkat
        replied = response_event.wait(timeout=timeout_sec)
    except Exception as e:
        print(f"[!] [SPEAKER AUDIT ERROR] Gagal koneksi/audit ke broker: {e}", flush=True)
        replied = False
    finally:
        if connected:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    status = "ONLINE" if replied else "OFFLINE"
    latency = audit_context["latency"]

    if replied:
        print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] [ALIVE/ONLINE] Perangkat {device_id} MERESPONS!", flush=True)
        print(f"   -> Latensi: {latency:.2f} detik", flush=True)
        print(f"   -> Topik Balasan: {audit_context['response_topic']}", flush=True)
        print(f"   -> Payload Balasan: {audit_context['response_payload'][:200]}", flush=True)
    else:
        print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] [DEAD/OFFLINE] Perangkat {device_id} TIDAK MERESPONS (Timeout {timeout_sec}s)", flush=True)

    # 1. Update Database Django (DeviceState)
    try:
        from devicestatusapp.models import DeviceState
        from django.utils import timezone as dj_tz
        DeviceState.objects.update_or_create(
            device_name=device_id,
            defaults={
                "status": status,
                "last_updated": dj_tz.now()
            }
        )
        print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [SPEAKER AUDIT] DeviceState di database diperbarui: {device_id} -> {status}", flush=True)
    except Exception as e:
        # Jika dipanggil di luar konteks Django
        pass

    result = {
        "device_id": device_id,
        "status": status,
        "is_alive": replied,
        "timestamp": timestamp_str,
        "timestamp_dt": now_dt,
        "latency_seconds": round(latency, 3) if latency is not None else None,
        "response_topic": audit_context["response_topic"],
        "response_payload": audit_context["response_payload"],
        "audit_topic": audit_topic,
        "broker": f"{broker}:{port}",
        "gsheet_synced": False,
    }

    # 2. Sinkronkan ke Google Sheet
    if sync_gsheet:
        try:
            synced = sync_audit_to_google_sheet(result, webhook_url=gsheet_url)
            result["gsheet_synced"] = synced
        except Exception as e:
            print(f"[!] [SPEAKER AUDIT] Gagal sinkronisasi Google Sheet: {e}", flush=True)

    # 3. Simpan ke File Excel Lokal
    if update_excel:
        try:
            excel_path = update_speaker_audit_excel_matrix(result)
            result["excel_path"] = excel_path
        except Exception as e:
            print(f"[!] [SPEAKER AUDIT] Gagal simpan Excel lokal: {e}", flush=True)

    LAST_AUDIT_RESULT = result
    return result


# ==============================================================================
# BACKGROUND SCHEDULER (TIAP 30 MENIT WIB: :00 dan :30)
# ==============================================================================
def start_speaker_audit_scheduler():
    """
    Menjalankan background scheduler loop yang otomatis melakukan audit perangkat
    setiap 30 menit (tepat di slot :00 dan :30 WIB).
    Menggantikan scheduler fatigue monitor 30 menit sebelumnya.
    """
    global _SCHEDULER_STARTED
    with _SCHEDULER_LOCK:
        if _SCHEDULER_STARTED:
            return
        _SCHEDULER_STARTED = True

    def _loop():
        # Jeda 5 detik saat inisialisasi awal server
        time.sleep(5)
        print("[SPEAKER AUDIT 30-MIN] Inisialisasi scheduler audit perangkat testing berhasil.", flush=True)
        
        # Eksekusi audit awal saat startup
        try:
            run_speaker_health_audit()
        except Exception as e:
            print(f"[SPEAKER AUDIT ERROR] Eksekusi awal gagal: {e}", flush=True)

        while True:
            sleep_sec = get_seconds_until_next_30min()
            menit = int(sleep_sec // 60)
            detik = int(sleep_sec % 60)
            print(f"[SPEAKER AUDIT 30-MIN] Menunggu interval 30 menit berikutnya ({menit}m {detik}s)...", flush=True)
            time.sleep(sleep_sec)
            try:
                run_speaker_health_audit()
            except Exception as ex:
                print(f"[SPEAKER AUDIT ERROR] Gagal menjalankan audit 30 menit: {ex}", flush=True)

    t = threading.Thread(target=_loop, daemon=True, name="SpeakerAuditScheduler")
    t.start()
    print("[SPEAKER AUDIT 30-MIN] Background thread 'SpeakerAuditScheduler' telah aktif.", flush=True)

