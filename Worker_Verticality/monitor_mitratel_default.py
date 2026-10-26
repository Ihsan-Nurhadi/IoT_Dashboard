"""
Service Monitoring Status Site (Mitratel Default) Berbasis Direct MQTT Listener & Google Spreadsheet Sync
==========================================================================================================
Logika Baru:
- Tidak lagi melakukan polling ke HTTP REST API.
- Langsung mendengarkan (listener) broker MQTT EMQX selama window 5 menit (300 detik) tiap satu jam (menit 00:00 - 05:00 WIB).
- Memantau apakah masing-masing dari 61 site mengirim data telemetri (tilt/wind/heartbeat/info) dalam interval tersebut.
  * Ada data dalam 5 menit -> Status = ONLINE
  * Tidak ada data sama sekali -> Status = OFFLINE
- Hasil monitoring otomatis di-sync ke:
  1. Google Spreadsheet (melalui Apps Script Webhook / Opsi A)
  2. File Excel Lokal (monitoring_mitratel_hourly.xlsx) untuk kompatibilitas dashboard internal NMS
- Setelah window 5 menit selesai, koneksi MQTT diputus dan worker tidur selama 55 menit hingga awal jam berikutnya.
"""

import argparse
from datetime import datetime, timezone, timedelta
import json
import os
import random
import re
import string
import sys
import time

# Pastikan output konsol mendukung UTF-8 di Windows PowerShell
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import paho.mqtt.client as mqtt
import requests

# ==============================================================================
# KONFIGURASI DEFAULT & ENVIRONMENT VARIABLES
# ==============================================================================
# Menggunakan prefix MITRATEL_MQTT_* agar TIDAK BENTROK dengan konfigurasi MQTT utama NMS
MQTT_BROKER = os.getenv("MITRATEL_MQTT_BROKER", os.getenv("MQTT_BROKER", "emqx.nayakanms.com"))
MQTT_PORT = int(os.getenv("MITRATEL_MQTT_PORT", os.getenv("MQTT_PORT", "1884")))
MQTT_USER = os.getenv("MITRATEL_MQTT_USER", os.getenv("MQTT_USER", "dmtver_jabo"))
MQTT_PASSWORD = os.getenv("MITRATEL_MQTT_PASSWORD", os.getenv("MQTT_PASSWORD", "jabo123"))

# Window durasi listening (default 300 detik = 5 menit)
DEFAULT_WINDOW_SECONDS = int(os.getenv("MITRATEL_LISTEN_WINDOW_SECONDS", os.getenv("LISTEN_WINDOW_SECONDS", "300")))
# Durasi saat manual trigger dari web (default 20 detik agar HTTP request tidak timeout)
MANUAL_WINDOW_SECONDS = int(os.getenv("MANUAL_WINDOW_SECONDS", "20"))

# Google Spreadsheet Webhook URL (Apps Script)
GSHEET_WEBHOOK_URL = os.getenv("GSHEET_WEBHOOK_URL", "")

# Filter simulator dummy: abaikan paket dari container simulator (IP 192.168.1.150 / fake online)
IGNORE_SIMULATOR_PACKETS = os.getenv("IGNORE_SIMULATOR_PACKETS", "true").lower() in ("true", "1", "yes")

# Path file output Excel lokal
DEFAULT_EXCEL_FILE = os.getenv(
    "EXCEL_OUTPUT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitoring_mitratel_hourly.xlsx"),
)
MEDIA_REPORTS_DIR = os.getenv("MEDIA_REPORTS_DIR", "")

# Zona waktu Indonesia Barat (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))


# ==============================================================================
# PEMUATAN DAFTAR 61 SITE MITRATEL
# ==============================================================================
def load_mitratel_sites() -> list[dict]:
    """
    Memuat daftar 61 site dari file sites_mitratel.json.
    Jika file belum ada di direktori kerja, mencari di direktori alternatif atau fallback.
    """
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites_mitratel.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "sites_mitratel.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "Worker_Verticality", "sites_mitratel.json"),
        "/app/sites_mitratel.json",
        "/app/Worker_Verticality/sites_mitratel.json",
        "sites_mitratel.json",
    ]

    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    sites = json.load(f)
                    if isinstance(sites, list) and len(sites) > 0:
                        return sites
            except Exception as e:
                print(f"[!] Warning reading {p}: {e}")

    # Fallback darurat jika file json tidak ditemukan
    print("[!] Warning: sites_mitratel.json tidak ditemukan, menggunakan dataset bawaan.")
    return []


def get_seconds_until_next_hour() -> float:
    """
    Menghitung jumlah detik hingga tepat awal jam berikutnya (menit 00:00 WIB).
    Menambahkan buffer 1.5 detik untuk memastikan jam sudah berganti saat bangun.
    """
    now = datetime.now(WIB)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    diff = (next_hour - now).total_seconds()
    return max(5.0, diff + 1.5)


# ==============================================================================
# MQTT LISTENER WINDOW (5 MENIT TIAP JAM)
# ==============================================================================
def run_mqtt_window_listener(
    duration_sec: int = DEFAULT_WINDOW_SECONDS,
    broker: str = MQTT_BROKER,
    port: int = MQTT_PORT,
    username: str = MQTT_USER,
    password: str = MQTT_PASSWORD,
) -> dict[str, dict]:
    """
    Membuka koneksi MQTT ke broker EMQX, mendengarkan data dari seluruh site selama
    duration_sec detik, lalu menutup koneksi secara bersih.
    
    Mengembalikan dictionary data telemetri yang berhasil ditangkap:
    {
        "E32_VER_PEDURENAN": {"count": 12, "last_topic": "...", "last_seen": "..."},
        ...
    }
    """
    received_telemetry: dict[str, dict] = {}
    random_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    client_id = f"mitratel_mon_{random_id}"

    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id
        )
    except AttributeError:
        client = mqtt.Client(client_id=client_id)

    if username and password:
        client.username_pw_set(username, password)

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Terhubung ke MQTT Broker: {broker}:{port}")
            # Subscribe ke topik telemetri verticality
            c.subscribe("nms/+/vertical/#")
            c.subscribe("nms/#")
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Subscribed ke topic nms/+/vertical/# (Window: {duration_sec} detik)")
        else:
            print(f"[!] Gagal koneksi ke MQTT broker, rc = {rc}")

    def on_message(c, userdata, msg):
        # 1. ABAIKAN pesan retained (pesan lama yang tersimpan di broker dari masa lalu)
        # Hanya hitung data live yang benar-benar dikirimkan perangkat selama window 5 menit
        if getattr(msg, "retain", False):
            return

        # 2. ABAIKAN paket dari simulator dashboard ("fake online" / IP 192.168.1.150)
        # Menjamin hanya perangkat keras lapangan asli yang tercatat ONLINE
        if IGNORE_SIMULATOR_PACKETS:
            try:
                payload_str = msg.payload.decode('utf-8', errors='ignore').strip()
                if payload_str.startswith("{") and payload_str.endswith("}"):
                    data = json.loads(payload_str)
                    if isinstance(data, dict):
                        src_ip = str(data.get("ip") or data.get("IP") or "")
                        if src_ip == "192.168.1.150":
                            # Paket berasal dari simulator (bukan hardware fisik), abaikan!
                            return
            except Exception:
                pass

        topic = msg.topic
        parts = topic.split("/")
        if len(parts) >= 2 and parts[0] == "nms":
            cid = parts[1].strip()
            leaf = parts[3].lower() if len(parts) >= 4 else (parts[2].lower() if len(parts) >= 3 else "")
            now_str = datetime.now(WIB).strftime("%H:%M:%S")

            if cid not in received_telemetry:
                received_telemetry[cid] = {
                    "count": 1,
                    "first_seen": now_str,
                    "last_seen": now_str,
                    "last_topic": topic,
                    "has_tilt": "tilt" in leaf,
                    "has_wind": "wind" in leaf,
                }
            else:
                received_telemetry[cid]["count"] += 1
                received_telemetry[cid]["last_seen"] = now_str
                received_telemetry[cid]["last_topic"] = topic
                if "tilt" in leaf:
                    received_telemetry[cid]["has_tilt"] = True
                if "wind" in leaf:
                    received_telemetry[cid]["has_wind"] = True

    client.on_connect = on_connect
    client.on_message = on_message

    print("=" * 70)
    print(f"  MEMULAI MQTT LISTENER WINDOW ({duration_sec} DETIK / {round(duration_sec/60, 1)} MENIT)")
    print(f"  Waktu Mulai: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S WIB')}")
    print("=" * 70)

    start_time = time.time()
    connected = False
    max_retries = 6
    retry_delay_sec = 5.0
    attempt = 1

    # Auto-retry koneksi ke MQTT broker
    while not connected and attempt <= max_retries:
        # Pastikan masih ada sisa waktu window
        if (time.time() - start_time) >= duration_sec:
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [!] Waktu window habis sebelum berhasil terhubung ke MQTT broker.")
            break

        try:
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] Menghubungkan ke MQTT Broker {broker}:{port} (Percobaan {attempt}/{max_retries})...")
            client.connect(broker, port, keepalive=60)
            client.loop_start()
            connected = True
            break
        except Exception as e:
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [!] Gagal koneksi MQTT ({e}).")
            if attempt < max_retries and (time.time() - start_time + retry_delay_sec < duration_sec):
                print(f"  Mencoba kembali dalam {int(retry_delay_sec)} detik...")
                time.sleep(retry_delay_sec)
                attempt += 1
            else:
                break

    if not connected:
        print("=" * 70)
        print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [!] FATAL: Gagal terhubung ke MQTT broker setelah {attempt} percobaan.")
        print(f"  Broker: {broker}:{port} tidak merespons atau sedang down.")
        print("=" * 70)
        return received_telemetry

    try:
        # Hitung mundur sisa waktu window listener
        while time.time() - start_time < duration_sec:
            elapsed = int(time.time() - start_time)
            remaining = duration_sec - elapsed
            if elapsed > 0 and elapsed % 30 == 0:
                print(f"  [Progress] Window aktif: {elapsed}s/{duration_sec}s | Site aktif terdeteksi: {len(received_telemetry)}")
            time.sleep(1.0)

    except Exception as e:
        print(f"[!] Error pada MQTT listener loop: {e}")
    finally:
        try:
            client.loop_stop()
            client.disconnect()
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] MQTT Listener selesai & koneksi ditutup.")
        except Exception:
            pass

    return received_telemetry


# ==============================================================================
# EVALUASI STATUS 61 SITE (ONLINE / OFFLINE)
# ==============================================================================
def evaluate_sites(sites: list[dict], telemetry_data: dict[str, dict]) -> tuple[list[dict], dict]:
    """
    Mencocokkan daftar 61 site dengan telemetry yang ditangkap selama window 5 menit.
    """
    evaluated = []
    online_count = 0
    offline_count = 0

    # Normalisasi keys telemetry_data menjadi huruf besar untuk case-insensitive matching
    upper_telemetry = {k.strip().upper(): v for k, v in telemetry_data.items()}

    for s in sites:
        site_item = dict(s)
        client_id = str(s.get("client_id", "")).strip()
        site_id = str(s.get("site_id", "")).strip()
        name = str(s.get("name", "")).strip()
        aliases = s.get("aliases") or []

        matched_telemetry = None

        # 1. Cek exact client_id
        if client_id and client_id.upper() in upper_telemetry:
            matched_telemetry = upper_telemetry[client_id.upper()]
        else:
            # 2. Cek aliases jika ada
            for alias in aliases:
                if alias and str(alias).strip().upper() in upper_telemetry:
                    matched_telemetry = upper_telemetry[str(alias).strip().upper()]
                    break

        if matched_telemetry:
            site_item["status"] = "ONLINE"
            site_item["message_count"] = matched_telemetry["count"]
            site_item["last_seen"] = matched_telemetry["last_seen"]
            site_item["last_topic"] = matched_telemetry["last_topic"]
            online_count += 1
        else:
            site_item["status"] = "OFFLINE"
            site_item["message_count"] = 0
            site_item["last_seen"] = "-"
            site_item["last_topic"] = "-"
            offline_count += 1

        evaluated.append(site_item)

    total_sites = len(evaluated)
    avail_rate = f"{(online_count / total_sites * 100):.1f}%" if total_sites > 0 else "0%"

    summary = {
        "total": total_sites,
        "online": online_count,
        "offline": offline_count,
        "availability": avail_rate,
    }

    return evaluated, summary


# ==============================================================================
# SINKRONISASI KE GOOGLE SPREADSHEET (APPS SCRIPT WEBHOOK)
# ==============================================================================
def sync_to_google_sheet(
    evaluated_sites: list[dict],
    summary: dict,
    waktu_tarik: datetime,
    webhook_url: str = "",
) -> bool:
    """
    Mengirimkan hasil monitoring matriks jam ke Google Spreadsheet via Apps Script Webhook.
    """
    url = webhook_url or GSHEET_WEBHOOK_URL or os.getenv("GSHEET_WEBHOOK_URL", "")
    if not url:
        print("[i] GSHEET_WEBHOOK_URL belum diset. Melewati sinkronisasi Google Spreadsheet.")
        return False

    date_str = waktu_tarik.strftime("%Y-%m-%d")
    hour_str = waktu_tarik.strftime("%H:00")
    timestamp_str = waktu_tarik.strftime("%Y-%m-%d %H:%M:%S WIB")

    payload = {
        "date": date_str,
        "hour": hour_str,
        "timestamp": timestamp_str,
        "summary": summary,
        "sites": evaluated_sites,
    }

    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] Mengirim data ke Google Spreadsheet ({url[:45]}...)...")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25
            )
            if res.status_code == 200:
                print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Sukses update Google Spreadsheet: {res.text[:120]}")
                return True
            else:
                print(f"[!] Gagal update Google Sheet: HTTP {res.status_code} (Percobaan {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(3 * attempt)
        except Exception as e:
            print(f"[!] Error koneksi ke Google Apps Script: {e} (Percobaan {attempt}/{max_retries})")
            if attempt < max_retries:
                time.sleep(3 * attempt)

    return False


# ==============================================================================
# SINKRONISASI KE FILE EXCEL LOKAL (MATRIKS HORIZONTAL JAM)
# ==============================================================================
def update_hourly_excel_matrix(
    sites: list[dict],
    waktu_tarik: datetime,
    file_path: str = DEFAULT_EXCEL_FILE,
    align_hour: bool = True,
    media_dir: str = MEDIA_REPORTS_DIR,
) -> str:
    """
    Menyimpan atau memperbarui data monitoring ke dalam matriks Excel horizontal:
    Kolom: [Nama Site] | [Site Code] | [Client ID] | [Regional] | [00:00] | [01:00] | ...
    Tiap sheet dinamai berdasarkan tanggal (YYYY-MM-DD).
    """
    sheet_name = waktu_tarik.strftime("%Y-%m-%d")
    hour_header = waktu_tarik.strftime("%H:00") if align_hour else waktu_tarik.strftime("%H:%M")

    dir_path = os.path.dirname(os.path.abspath(file_path))
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)

    fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_header_hour = PatternFill(start_color="2C5E8A", end_color="2C5E8A", fill_type="solid")
    fill_zebra = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    fill_online = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    font_online = Font(name="Calibri", size=10, bold=True, color="2E7D32")

    fill_offline = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
    font_offline = Font(name="Calibri", size=10, bold=True, color="C62828")

    thin_border_side = Side(border_style="thin", color="D1D5DB")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

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

    ws.views.sheetView[0].showGridLines = True

    is_new_sheet = (ws.max_row < 2 or ws.cell(row=1, column=1).value is None)

    # Dictionary site mapping status
    site_status_map = {}
    for s in sites:
        scode = str(s.get("site_id", "")).strip().upper()
        sname = str(s.get("name", "")).strip().upper()
        scid = str(s.get("client_id", "")).strip().upper()
        st = str(s.get("status", "OFFLINE")).upper()
        if scode: site_status_map[scode] = st
        if sname: site_status_map[sname] = st
        if scid: site_status_map[scid] = st

    if is_new_sheet:
        headers = ["Nama Site", "Site Code", "Client ID", "Regional"]
        for c_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=c_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        for idx, s in enumerate(sites, start=2):
            cell_name = ws.cell(row=idx, column=1, value=s.get("name", "-"))
            cell_code = ws.cell(row=idx, column=2, value=s.get("site_id", "-"))
            cell_cid  = ws.cell(row=idx, column=3, value=s.get("client_id", "-"))
            cell_reg  = ws.cell(row=idx, column=4, value=s.get("regional", "-"))

            cell_name.font = font_bold
            cell_name.border = thin_border
            cell_name.alignment = Alignment(horizontal="left", vertical="center")

            cell_code.font = font_regular
            cell_code.border = thin_border
            cell_code.alignment = Alignment(horizontal="center", vertical="center")

            cell_cid.font = font_regular
            cell_cid.border = thin_border
            cell_cid.alignment = Alignment(horizontal="left", vertical="center")

            cell_reg.font = font_regular
            cell_reg.border = thin_border
            cell_reg.alignment = Alignment(horizontal="center", vertical="center")

            if idx % 2 == 0:
                cell_name.fill = fill_zebra
                cell_code.fill = fill_zebra
                cell_cid.fill = fill_zebra
                cell_reg.fill = fill_zebra

        target_col = 5
    else:
        # Cari apakah kolom untuk jam ini sudah ada
        target_col = None
        for col in range(5, ws.max_column + 1):
            val = str(ws.cell(row=1, column=col).value or "").strip()
            if val == hour_header:
                target_col = col
                break
        if target_col is None:
            target_col = max(5, ws.max_column + 1)

    # Tulis header jam
    header_cell = ws.cell(row=1, column=target_col, value=hour_header)
    header_cell.font = font_header
    header_cell.fill = fill_header_hour
    header_cell.alignment = Alignment(horizontal="center", vertical="center")
    header_cell.border = thin_border

    # Isi status untuk tiap baris site
    for r in range(2, ws.max_row + 1):
        site_name_val = str(ws.cell(row=r, column=1).value or "").strip().upper()
        site_code_val = str(ws.cell(row=r, column=2).value or "").strip().upper()
        site_cid_val  = str(ws.cell(row=r, column=3).value or "").strip().upper()

        status_val = site_status_map.get(site_cid_val) or site_status_map.get(site_code_val) or site_status_map.get(site_name_val) or "OFFLINE"

        status_cell = ws.cell(row=r, column=target_col, value=status_val)
        status_cell.alignment = Alignment(horizontal="center", vertical="center")
        status_cell.border = thin_border

        if status_val == "ONLINE":
            status_cell.fill = fill_online
            status_cell.font = font_online
        else:
            status_cell.fill = fill_offline
            status_cell.font = font_offline

    # Auto-adjust lebar kolom
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        if col[0].column <= 4:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
        else:
            ws.column_dimensions[col_letter].width = 11

    # Freeze panes
    ws.freeze_panes = "E2"

    wb.save(file_path)
    print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Berhasil menyimpan file Excel lokal: {file_path}")

    # Salin ke media dir jika ada
    if media_dir and os.path.exists(media_dir):
        try:
            import shutil
            dest_file = os.path.join(media_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_file)
            print(f"[{datetime.now(WIB).strftime('%H:%M:%S')}] [OK] Salinan file Excel di-sync ke: {dest_file}")
        except Exception as e:
            print(f"[!] Gagal menyalin ke media dir: {e}")

    return file_path


# ==============================================================================
# ENTRY POINT FUNGSI SINGLE MONITORING (DIGUNAKAN OLEH BACKEND TRIGGER JUGA)
# ==============================================================================
def run_single_monitoring(
    file_path: str = DEFAULT_EXCEL_FILE,
    align_hour: bool = True,
    media_dir: str = MEDIA_REPORTS_DIR,
    duration_seconds: int = None,
    gsheet_url: str = None,
) -> str:
    """
    Menjalankan 1 siklus monitoring lengkap:
    1. Memuat daftar 61 site
    2. Mendengarkan data MQTT broker selama window tertentu
    3. Evaluasi status ONLINE/OFFLINE
    4. Sync ke Google Spreadsheet
    5. Update file Excel lokal
    """
    waktu_tarik = datetime.now(WIB)
    sites = load_mitratel_sites()
    if not sites:
        raise ValueError("Daftar 61 site Mitratel tidak ditemukan di sites_mitratel.json")

    # Tentukan durasi window (jika manual trigger cepat, gunakan MANUAL_WINDOW_SECONDS)
    window_sec = duration_seconds if duration_seconds is not None else MANUAL_WINDOW_SECONDS

    # 1. Dengarkan MQTT
    telemetry_data = run_mqtt_window_listener(duration_sec=window_sec)

    if not telemetry_data:
        print("[!] PERINGATAN: Tidak ada data telemetri yang berhasil ditangkap selama window listening.")

    # 2. Evaluasi
    evaluated_sites, summary = evaluate_sites(sites, telemetry_data)

    print("\n" + "=" * 70)
    print(f"  HASIL MONITORING MITRATEL ({waktu_tarik.strftime('%Y-%m-%d %H:%M:%S WIB')})")
    print(f"  Total Site: {summary['total']} | ONLINE: {summary['online']} | OFFLINE: {summary['offline']} | Availability: {summary['availability']}")
    print("=" * 70)

    # 3. Kirim ke Google Spreadsheet
    sync_to_google_sheet(evaluated_sites, summary, waktu_tarik, webhook_url=gsheet_url)

    # 4. Simpan ke Excel Lokal
    saved_path = update_hourly_excel_matrix(
        sites=evaluated_sites,
        waktu_tarik=waktu_tarik,
        file_path=file_path,
        align_hour=align_hour,
        media_dir=media_dir
    )

    return saved_path


# ==============================================================================
# MAIN SERVICE LOOP (24/7 TIAP JAM SELARAS MENIT 00)
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Service Monitoring Status Site (Mitratel Default) Berbasis MQTT & Google Sheets Sync."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Jalankan service terus-menerus 24/7 selaras pergantian jam (menit 00:00 - 05:00 WIB).",
    )
    parser.add_argument(
        "--align-hour",
        action="store_true",
        default=True,
        help="Gunakan header jam bulat (misal 08:00) alih-alih menit pengambilan saat ini.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_EXCEL_FILE,
        help="Path file output Excel lokal yang akan diperbarui.",
    )
    parser.add_argument(
        "--window-sec",
        type=int,
        default=DEFAULT_WINDOW_SECONDS,
        help=f"Durasi window listener dalam detik (default: {DEFAULT_WINDOW_SECONDS}s = 5 menit).",
    )
    parser.add_argument(
        "--gsheet-url",
        type=str,
        default=GSHEET_WEBHOOK_URL,
        help="Google Apps Script Webhook URL.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  NMS MITRATEL DEFAULT MONITORING SERVICE (MQTT & GOOGLE SHEETS)")
    print("=" * 70)
    print(f"  [OK] Broker       : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  [OK] Username     : {MQTT_USER}")
    print(f"  [OK] Window Durasi: {args.window_sec} detik (5 menit)")
    print(f"  [OK] Output Excel : {args.output}")
    print(f"  [OK] GSheet URL   : {args.gsheet_url[:40]}..." if args.gsheet_url else "  [OK] GSheet URL   : Belum diset (bisa via env GSHEET_WEBHOOK_URL)")
    print(f"  [OK] Mode Loop    : {'AKTIF (24/7)' if args.loop else 'EKSEKUSI TUNGGAL'}")
    print("=" * 70)

    if not args.loop:
        # Eksekusi sekali saja
        run_single_monitoring(
            file_path=args.output,
            align_hour=args.align_hour,
            media_dir=MEDIA_REPORTS_DIR,
            duration_seconds=args.window_sec,
            gsheet_url=args.gsheet_url,
        )
        sys.exit(0)

    # Mode 24/7 Loop Selaras Menit 00
    while True:
        try:
            # Hitung waktu tunggu hingga menit 00:00 jam berikutnya
            sleep_sec = get_seconds_until_next_hour()
            now_wib = datetime.now(WIB)
            target_time = now_wib + timedelta(seconds=sleep_sec)

            print(f"\n[{now_wib.strftime('%H:%M:%S')}] Menunggu hingga awal jam berikutnya: {target_time.strftime('%H:%M:00 WIB')} (Tidur {int(sleep_sec)}s / {round(sleep_sec/60, 1)} menit)...")
            time.sleep(sleep_sec)

            # Jam berganti! Jalankan window monitoring 5 menit
            run_single_monitoring(
                file_path=args.output,
                align_hour=args.align_hour,
                media_dir=MEDIA_REPORTS_DIR,
                duration_seconds=args.window_sec,
                gsheet_url=args.gsheet_url,
            )

        except KeyboardInterrupt:
            print("\n[!] Service dihentikan oleh user (KeyboardInterrupt).")
            break
        except Exception as e:
            print(f"[!] Error pada siklus utama monitoring: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
