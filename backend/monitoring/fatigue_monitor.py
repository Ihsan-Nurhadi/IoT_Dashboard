"""
Service Monitoring Status Fatigue / Verticality Sites (30-Minute Matrix Excel).
Mencatat status ONLINE / OFFLINE seluruh site verticality per 30 menit (00:00, 00:30, ...)
ke dalam matriks horizontal Excel berformat sheet harian (YYYY-MM-DD).
"""
import os
import time
import threading
from datetime import datetime, timezone, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.conf import settings
from django.utils import timezone as dj_timezone

# Zona waktu Indonesia Barat (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))


def get_fatigue_excel_path() -> str:
    """Mengembalikan path file Excel monitoring fatigue 30 menit."""
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    return os.path.join(reports_dir, 'monitoring_fatigue_30min.xlsx')


def get_seconds_until_next_30min() -> float:
    """
    Menghitung jumlah detik hingga slot 30 menit berikutnya (menit :00 atau :30 WIB).
    Menambahkan buffer 1 detik untuk memastikan waktu telah berpindah.
    """
    now = datetime.now(WIB)
    current_minute = now.minute
    if current_minute < 30:
        next_target = now.replace(minute=30, second=0, microsecond=0)
    else:
        next_target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    diff = (next_target - now).total_seconds()
    return max(3.0, diff + 1.0)


def get_fatigue_sites_with_status() -> list[dict]:
    """
    Mengambil site Verticality E32_VER_WEES dan mengecek status ONLINE / OFFLINE.
    Sebuah site dianggap ONLINE jika menerima data SensorData dalam 5 menit terakhir.
    """
    from monitoring.models import SensorData

    now = dj_timezone.now()
    threshold_online = now - timedelta(minutes=5)

    latest_reading = (
        SensorData.objects
        .filter(device_id='E32_VER_WEES')
        .order_by('-timestamp')
        .first()
    )

    last_ts = latest_reading.timestamp if latest_reading else None
    is_online = (last_ts is not None and last_ts >= threshold_online)

    return [{
        "name": "Nayaka WEES",
        "siteId": "20TS10B1529",
        "code": "E32_VER_WEES",
        "status": "ONLINE" if is_online else "OFFLINE",
        "last_seen": last_ts
    }]


def update_fatigue_excel_matrix(
    file_path: str = None,
    align_30min: bool = True
) -> dict:
    """
    Menyimpan atau memperbarui data status site fatigue ke matriks Excel horizontal per 30 menit.
    Kolom: [Nama Site] | [Site ID] | [Device Code] | [00:00] | [00:30] | [01:00] | ...
    Tiap sheet dinamai berdasarkan tanggal hari ini (YYYY-MM-DD).
    """
    if not file_path:
        file_path = get_fatigue_excel_path()

    waktu_tarik = datetime.now(WIB)
    sheet_name = waktu_tarik.strftime("%Y-%m-%d")

    # Format header waktu:
    # Jika align_30min: dibulatkan ke :00 atau :30
    if align_30min:
        slot_minute = "30" if waktu_tarik.minute >= 30 else "00"
        slot_header = f"{waktu_tarik.hour:02d}:{slot_minute}"
    else:
        slot_header = waktu_tarik.strftime("%H:%M")

    # Pastikan direktori folder tersedia
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    # Styling Elements
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)

    fill_header = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    fill_header_slot = PatternFill(start_color="2C5E8A", end_color="2C5E8A", fill_type="solid")
    fill_zebra = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    fill_online = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
    font_online = Font(name="Calibri", size=10, bold=True, color="2E7D32")

    fill_offline = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")
    font_offline = Font(name="Calibri", size=10, bold=True, color="C62828")

    thin_border_side = Side(border_style="thin", color="D1D5DB")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # 1. Buka atau buat Workbook baru
    if os.path.exists(file_path):
        try:
            wb = openpyxl.load_workbook(file_path)
        except Exception:
            wb = openpyxl.Workbook()
    else:
        wb = openpyxl.Workbook()

    # 2. Ambil atau buat Sheet untuk tanggal hari ini
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        if len(wb.sheetnames) == 1 and wb.sheetnames[0] == "Sheet":
            ws = wb.active
            ws.title = sheet_name
        else:
            ws = wb.create_sheet(title=sheet_name)

    ws.views.sheetView[0].showGridLines = True

    # 3. Ambil data status seluruh site saat ini
    sites_data = get_fatigue_sites_with_status()
    api_site_map = {s["code"]: s["status"] for s in sites_data}
    for s in sites_data:
        api_site_map[s["name"]] = s["status"]
        api_site_map[s["siteId"]] = s["status"]

    is_new_sheet = (ws.max_row < 2 or ws.cell(row=1, column=1).value is None)

    if is_new_sheet:
        # Tulis Header Dasar
        headers = ["Nama Site", "Site ID", "Device Code"]
        for c_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=c_idx, value=h_text)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # Tulis Baris Site
        sorted_sites = sorted(sites_data, key=lambda x: str(x.get("name", "")).lower())
        for idx, s in enumerate(sorted_sites, start=2):
            cell_name = ws.cell(row=idx, column=1, value=s.get("name", "-"))
            cell_site_id = ws.cell(row=idx, column=2, value=s.get("siteId", "-"))
            cell_code = ws.cell(row=idx, column=3, value=s.get("code", "-"))

            cell_name.font = font_bold
            cell_name.border = thin_border
            cell_name.alignment = Alignment(horizontal="left", vertical="center")

            cell_site_id.font = font_regular
            cell_site_id.border = thin_border
            cell_site_id.alignment = Alignment(horizontal="center", vertical="center")

            cell_code.font = font_regular
            cell_code.border = thin_border
            cell_code.alignment = Alignment(horizontal="center", vertical="center")

            if idx % 2 == 0:
                cell_name.fill = fill_zebra
                cell_site_id.fill = fill_zebra
                cell_code.fill = fill_zebra

        target_col = 4
    else:
        # Pastikan sheet hanya berisi baris untuk site E32_VER_WEES
        while ws.max_row > 2:
            ws.delete_rows(ws.max_row)

        # Pastikan baris 2 adalah E32_VER_WEES
        ws.cell(row=2, column=1, value="Nayaka WEES")
        ws.cell(row=2, column=2, value="20TS10B1529")
        ws.cell(row=2, column=3, value="E32_VER_WEES")

        # Cari kolom slot yang sesuai jika sudah ada (timpa nilai)
        target_col = None
        for col_idx in range(4, ws.max_column + 1):
            col_val = str(ws.cell(row=1, column=col_idx).value or "").strip()
            if col_val == slot_header:
                target_col = col_idx
                break

        if target_col is None:
            target_col = ws.max_column + 1

    # 4. Tulis Header Jam / Interval 30 Menit
    header_cell = ws.cell(row=1, column=target_col, value=slot_header)
    header_cell.font = font_header
    header_cell.fill = fill_header_slot
    header_cell.alignment = Alignment(horizontal="center", vertical="center")
    header_cell.border = thin_border
    ws.row_dimensions[1].height = 26

    # 5. Tulis Status tiap baris site untuk interval ini
    online_count = 0
    offline_count = 0
    for row_idx in range(2, ws.max_row + 1):
        site_name_val = str(ws.cell(row=row_idx, column=1).value or "").strip()
        site_id_val = str(ws.cell(row=row_idx, column=2).value or "").strip()
        site_code_val = str(ws.cell(row=row_idx, column=3).value or "").strip()

        status = api_site_map.get(site_code_val) or api_site_map.get(site_name_val) or api_site_map.get(site_id_val) or "OFFLINE"

        cell = ws.cell(row=row_idx, column=target_col, value=status)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        ws.row_dimensions[row_idx].height = 20

        if status == "ONLINE":
            cell.fill = fill_online
            cell.font = font_online
            online_count += 1
        else:
            cell.fill = fill_offline
            cell.font = font_offline
            offline_count += 1

    # Freeze panes pada kolom D dan baris 1 (Informasi site tetap terlihat saat scroll ke kanan)
    ws.freeze_panes = "D2"

    # Atur lebar kolom
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 24
    for col_i in range(4, ws.max_column + 1):
        col_letter = get_column_letter(col_i)
        ws.column_dimensions[col_letter].width = 12

    # Simpan file Excel
    wb.save(file_path)

    return {
        "saved_file": file_path,
        "slot": slot_header,
        "timestamp": waktu_tarik.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "total_sites": len(sites_data),
        "online_count": online_count,
        "offline_count": offline_count,
    }


_SCHEDULER_STARTED = False

def start_fatigue_matrix_background_scheduler():
    """Menjalankan background scheduler loop yang otomatis mencatat data setiap 30 menit."""
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return
    _SCHEDULER_STARTED = True

    def _loop():
        # Berikan jeda 5 detik saat inisialisasi awal server
        time.sleep(5)
        # Jalankan pencatatan awal saat server start
        try:
            update_fatigue_excel_matrix(align_30min=True)
            print("[FATIGUE MONITOR 30-MIN] Inisialisasi data awal berhasil.")
        except Exception as e:
            print(f"[FATIGUE MONITOR 30-MIN ERROR] Inisialisasi awal gagal: {e}")

        while True:
            sleep_sec = get_seconds_until_next_30min()
            menit = int(sleep_sec // 60)
            detik = int(sleep_sec % 60)
            print(f"[FATIGUE MONITOR 30-MIN] Menunggu interval 30 menit berikutnya ({menit}m {detik}s)...")
            time.sleep(sleep_sec)
            try:
                res = update_fatigue_excel_matrix(align_30min=True)
                print(f"[FATIGUE MONITOR 30-MIN] Sukses mencatat slot '{res.get('slot')} WIB': {res.get('online_count')} Online, {res.get('offline_count')} Offline.")
            except Exception as ex:
                print(f"[FATIGUE MONITOR 30-MIN ERROR] Gagal update siklus 30 menit: {ex}")

    t = threading.Thread(target=_loop, daemon=True, name="FatigueMatrixScheduler")
    t.start()
