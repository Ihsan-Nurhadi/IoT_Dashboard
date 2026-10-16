import argparse
from datetime import datetime, timezone, timedelta
import os
import re
import sys
import time
import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# KONFIGURASI DEFAULT & ENVIRONMENT VARIABLES
# ==============================================================================
DEFAULT_API_KEY = os.getenv(
    "MAIVIEW_API_KEY",
    "nms_live_0c05c2b6_d09b6897332bcc9fde952de761b6e15ba8cb9366817b22231ca126a2b933106a",
)
API_URL = os.getenv("MAIVIEW_API_URL", "https://api.maiviewmitratel.id/v1/sites")
DEFAULT_BRANCH = os.getenv("MONITOR_BRANCH", "Mitratel Default")
DEFAULT_EXCEL_FILE = os.getenv(
    "EXCEL_OUTPUT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "monitoring_mitratel_hourly.xlsx"),
)
MEDIA_REPORTS_DIR = os.getenv("MEDIA_REPORTS_DIR", "")

# Daftar Site Khusus Tambahan yang ikut dimonitor (meskipun di luar branch default)
EXTRA_SITE_IDS = [
    "bd3deb2d-6e81-5540-9eed-04fd397d5ca6",  # dmt new ikn (DMT_NEW_IKN)
    "83a838ed-698f-414a-a37c-5669f5a1e4b6",  # dmt isat tamangapa (DMT ISAT_TAMANGAPA)
    "347e50b4-eabb-46f0-a96d-a9da03934119",  # margodadii (MARGODADI)
    "575e8551-5e53-5c3d-abb2-39984e5cd8db",  # pelab ajibata (PELAB AJIBATA)
    "c6dc7fe4-8d26-5587-9101-1ead5d9faf65",  # dagang kelambir (Dagang Kelambir)
    "ea5ae5e7-a752-501a-99db-b0738bf9daa2",  # permanenisasi (PERMANENISASICIOKONGSUKARESIKSIDAMULIH)
    "661cc75b-37ec-539d-9197-853f91dd7f16",  # jalanmustikasari (JALANMUSTIKASARI)
    "ee11245f-deb1-43fe-abc1-d5d52d399053",  # nayakaws
]

# Zona waktu Indonesia Barat (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))


def clean_auth_token(token: str) -> str:
    """Membersihkan prefix Bearer jika ada."""
    if not token:
        return ""
    return re.sub(r"(?i)^bearer\s+", "", token).strip()


def get_seconds_until_next_hour() -> float:
    """
    Menghitung jumlah detik hingga tepat awal jam berikutnya (menit 00:00 WIB).
    Menambahkan buffer 1.5 detik untuk memastikan jam sudah berganti saat bangun.
    """
    now = datetime.now(WIB)
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    diff = (next_hour - now).total_seconds()
    return max(5.0, diff + 1.5)


def fetch_sites_by_branch(api_key: str, branch_name: str = DEFAULT_BRANCH) -> tuple[list[dict], datetime]:
    """
    Menarik seluruh data site dari API MaiView dan memfilter branch yang diminta.
    Dilengkapi mekanisme auto-retry 3x jika koneksi timeout / error.
    """
    clean_key = clean_auth_token(api_key)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {clean_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MaiView-Monitor/1.0",
    }

    waktu_tarik = datetime.now(WIB)
    all_sites = []
    page = 1
    per_page = 100
    max_retries = 3

    while True:
        params = {"page": page, "per_page": per_page, "is_active": "true"}
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(API_URL, headers=headers, params=params, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("data") or []
                    all_sites.extend(items)
                    success = True
                    if len(items) < per_page:
                        break
                    page += 1
                    break
                else:
                    print(f"[!] Gagal halaman {page}: HTTP {res.status_code} (Percobaan {attempt}/{max_retries})")
                    if attempt < max_retries:
                        time.sleep(3 * attempt)
            except requests.RequestException as e:
                print(f"[!] Error koneksi API halaman {page}: {e} (Percobaan {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(3 * attempt)

        if not success or (success and len(items) < per_page):
            break

    target_clean = branch_name.strip().lower()
    extra_set = set(EXTRA_SITE_IDS)
    filtered_sites = [
        s for s in all_sites
        if (
            str(s.get("branch_name", "")).strip().lower() == target_clean
            or s.get("id") in extra_set
        )
    ]
    return filtered_sites, waktu_tarik


def update_hourly_excel_matrix(
    sites: list[dict],
    waktu_tarik: datetime,
    file_path: str = DEFAULT_EXCEL_FILE,
    align_hour: bool = True,
    media_dir: str = MEDIA_REPORTS_DIR,
) -> str:
    """
    Menyimpan atau memperbarui data monitoring ke dalam matriks Excel horizontal:
    Kolom: [Nama Site] | [Site Code] | [08:00] | [09:00] | [10:00] | ...
    Tiap sheet dinamai berdasarkan tanggal (YYYY-MM-DD).
    """
    sheet_name = waktu_tarik.strftime("%Y-%m-%d")
    hour_header = waktu_tarik.strftime("%H:00") if align_hour else waktu_tarik.strftime("%H:%M")

    # Pastikan folder target ada
    dir_path = os.path.dirname(os.path.abspath(file_path))
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

    # Styling Elements
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

    # 1. Buka file yang sudah ada atau buat Workbook baru
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

    # 3. Cek apakah tabel sudah memiliki header dasar (Nama Site, Site Code)
    is_new_sheet = (ws.max_row < 2 or ws.cell(row=1, column=1).value is None)

    # Dictionary site saat ini dari API: {site_code: status, name: status}
    api_site_map = {}
    for s in sites:
        scode = str(s.get("site_code", "")).strip()
        sname = str(s.get("name", "")).strip()
        sstatus = str(s.get("status", "-")).upper()
        api_site_map[scode] = sstatus
        api_site_map[sname] = sstatus

    if is_new_sheet:
        # Tulis Header Dasar
        ws.cell(row=1, column=1, value="Nama Site").font = font_header
        ws.cell(row=1, column=1).fill = fill_header
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=1, column=1).border = thin_border

        ws.cell(row=1, column=2, value="Site Code").font = font_header
        ws.cell(row=1, column=2).fill = fill_header
        ws.cell(row=1, column=2).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=1, column=2).border = thin_border

        # Urutkan site berdasarkan nama
        sorted_sites = sorted(sites, key=lambda x: str(x.get("name", "")).lower())

        for idx, s in enumerate(sorted_sites, start=2):
            cell_name = ws.cell(row=idx, column=1, value=s.get("name", "-"))
            cell_code = ws.cell(row=idx, column=2, value=s.get("site_code", "-"))
            
            cell_name.font = font_bold
            cell_name.border = thin_border
            cell_name.alignment = Alignment(horizontal="left", vertical="center")

            cell_code.font = font_regular
            cell_code.border = thin_border
            cell_code.alignment = Alignment(horizontal="center", vertical="center")

            if idx % 2 == 0:
                cell_name.fill = fill_zebra
                cell_code.fill = fill_zebra

        target_col = 3
    else:
        # Cek apakah ada site baru yang belum terdaftar di sheet saat ini
        existing_site_names = set()
        existing_site_codes = set()
        for r in range(2, ws.max_row + 1):
            s_name_val = str(ws.cell(row=r, column=1).value or "").strip().lower()
            s_code_val = str(ws.cell(row=r, column=2).value or "").strip().lower()
            if s_name_val:
                existing_site_names.add(s_name_val)
            if s_code_val:
                existing_site_codes.add(s_code_val)

        # Tambahkan baris baru untuk site yang belum ada
        for s in sites:
            s_name = str(s.get("name", "")).strip()
            s_code = str(s.get("site_code", "")).strip()
            if s_name.lower() not in existing_site_names and s_code.lower() not in existing_site_codes:
                new_row = ws.max_row + 1
                cell_name = ws.cell(row=new_row, column=1, value=s_name)
                cell_code = ws.cell(row=new_row, column=2, value=s_code)
                cell_name.font = font_bold
                cell_name.border = thin_border
                cell_name.alignment = Alignment(horizontal="left", vertical="center")
                cell_code.font = font_regular
                cell_code.border = thin_border
                cell_code.alignment = Alignment(horizontal="center", vertical="center")
                if new_row % 2 == 0:
                    cell_name.fill = fill_zebra
                    cell_code.fill = fill_zebra
                existing_site_names.add(s_name.lower())
                existing_site_codes.add(s_code.lower())

        # Cari apakah kolom dengan header jam ini sudah ada sebelumnya (timpa jika ada)
        target_col = None
        for col_idx in range(3, ws.max_column + 1):
            col_val = str(ws.cell(row=1, column=col_idx).value or "").strip()
            if col_val == hour_header:
                target_col = col_idx
                break
        
        # Jika belum ada, gunakan kolom kosong baru paling kanan
        if target_col is None:
            target_col = ws.max_column + 1

    # 4. Tulis Header Jam di kolom target
    header_cell = ws.cell(row=1, column=target_col, value=hour_header)
    header_cell.font = font_header
    header_cell.fill = fill_header_hour
    header_cell.alignment = Alignment(horizontal="center", vertical="center")
    header_cell.border = thin_border
    ws.row_dimensions[1].height = 26

    # 5. Tulis Status tiap baris site untuk jam ini
    for row_idx in range(2, ws.max_row + 1):
        site_name_val = str(ws.cell(row=row_idx, column=1).value or "").strip()
        site_code_val = str(ws.cell(row=row_idx, column=2).value or "").strip()

        status = api_site_map.get(site_code_val) or api_site_map.get(site_name_val) or "-"
        
        cell = ws.cell(row=row_idx, column=target_col, value=status)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        ws.row_dimensions[row_idx].height = 20

        if status == "ONLINE":
            cell.fill = fill_online
            cell.font = font_online
        elif status == "OFFLINE":
            cell.fill = fill_offline
            cell.font = font_offline
        else:
            cell.font = font_regular

    # Freeze panes pada kolom B dan baris 1 (Nama site tetap kelihatan saat di-scroll ke kanan)
    ws.freeze_panes = "C2"

    # Atur lebar kolom
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 16
    for col_i in range(3, ws.max_column + 1):
        col_letter = get_column_letter(col_i)
        ws.column_dimensions[col_letter].width = 12

    # Simpan file utama
    saved = False
    for attempt in range(1, 4):
        try:
            wb.save(file_path)
            saved = True
            break
        except PermissionError:
            print(f"[!] PERINGATAN: File '{file_path}' terkunci program lain. Mencoba ulang dalam 5 detik...")
            time.sleep(5)
        except Exception as e:
            print(f"[!] Gagal menyimpan file Excel: {e}")
            break

    # Salin atau simpan juga ke direktori media reports jika dikonfigurasi
    if saved and media_dir:
        try:
            os.makedirs(media_dir, exist_ok=True)
            media_file = os.path.join(media_dir, os.path.basename(file_path))
            wb.save(media_file)
            print(f"[+] Salinan berhasil disimpan ke media directory: {media_file}")
        except Exception as e:
            print(f"[!] Gagal menyalin ke media directory: {e}")

    return os.path.abspath(file_path)


def run_single_monitoring(
    api_key: str = DEFAULT_API_KEY,
    branch_name: str = DEFAULT_BRANCH,
    file_path: str = DEFAULT_EXCEL_FILE,
    align_hour: bool = True,
    media_dir: str = MEDIA_REPORTS_DIR,
) -> str | None:
    """Menjalankan satu kali siklus penarikan data dan update Excel."""
    sites, waktu_tarik = fetch_sites_by_branch(api_key=api_key, branch_name=branch_name)
    if not sites:
        print(f"[!] Tidak ada site yang ditemukan untuk branch '{branch_name}'.")
        return None

    saved_file = update_hourly_excel_matrix(
        sites=sites,
        waktu_tarik=waktu_tarik,
        file_path=file_path,
        align_hour=align_hour,
        media_dir=media_dir,
    )

    online_cnt = sum(1 for s in sites if str(s.get("status", "")).lower() == "online")
    offline_cnt = sum(1 for s in sites if str(s.get("status", "")).lower() == "offline")
    jam_str = waktu_tarik.strftime("%H:00 WIB") if align_hour else waktu_tarik.strftime("%H:%M WIB")

    print(f"[{waktu_tarik.strftime('%Y-%m-%d %H:%M:%S')} WIB] Berhasil update kolom jam '{jam_str}'")
    print(f"  -> Total: {len(sites)} site | Online: {online_cnt} | Offline: {offline_cnt}")
    print(f"  -> File Excel: {saved_file}\n")
    return saved_file


def main():
    parser = argparse.ArgumentParser(
        description="Service Monitoring Status Site (Mitratel Default) Matriks Jam Excel."
    )
    parser.add_argument(
        "--api-key",
        "-k",
        default=DEFAULT_API_KEY,
        help="API Key MaiView.",
    )
    parser.add_argument(
        "--branch",
        "-b",
        default=DEFAULT_BRANCH,
        help=f"Nama branch (default: '{DEFAULT_BRANCH}').",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_EXCEL_FILE,
        help=f"Nama file Excel matriks (default: '{DEFAULT_EXCEL_FILE}').",
    )
    parser.add_argument(
        "--media-dir",
        "-m",
        default=MEDIA_REPORTS_DIR,
        help="Direktori media bersama backend untuk download via browser.",
    )
    parser.add_argument(
        "--loop",
        "-l",
        action="store_true",
        help="Jalankan otomatis terus-menerus setiap 1 jam sekali (loop mode).",
    )
    parser.add_argument(
        "--align-hour",
        action="store_true",
        default=True,
        help="Selaraskan eksekusi tepat di menit 00 setiap pergantian jam (default: True).",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=3600,
        help="Interval perulangan dalam detik jika tidak menggunakan --align-hour (default: 3600 detik).",
    )

    args = parser.parse_args()

    print("=" * 75)
    print(f"{'MAIVIEW HOURLY MONITORING SERVICE (MATRIX EXCEL)':^75}")
    print(f"{'Branch: ' + args.branch:^75}")
    print("=" * 75)
    print(f"[*] Target File Excel : {args.output}")
    if args.media_dir:
        print(f"[*] Media Reports Dir : {args.media_dir}")
    print(f"[*] Mode Eksekusi     : {'Loop Otomatis 24/7' if args.loop else 'Single Run (1 kali eksekusi)'}")
    print(f"[*] Top-of-Hour Sync  : {'Aktif (Tepat Menit :00)' if args.align_hour else 'Interval Statis'}")
    print("-" * 75)

    if args.loop:
        print("[*] Service berjalan di background. Tekan Ctrl+C untuk menghentikan.\n")
        try:
            # 1. Jalankan langsung penarikan pertama saat service menyala
            print("[*] Menjalankan penarikan data awal saat service start...")
            run_single_monitoring(
                api_key=args.api_key,
                branch_name=args.branch,
                file_path=args.output,
                align_hour=args.align_hour,
                media_dir=args.media_dir,
            )

            # 2. Perulangan otomatis ke depan
            while True:
                if args.align_hour:
                    sleep_sec = get_seconds_until_next_hour()
                    menit = int(sleep_sec // 60)
                    detik = int(sleep_sec % 60)
                    print(f"[*] Menunggu jadwal jam berikutnya (dalam {menit} menit {detik} detik)...")
                    time.sleep(sleep_sec)
                else:
                    print(f"[*] Menunggu interval berikutnya ({args.interval // 60} menit)...")
                    time.sleep(args.interval)

                try:
                    run_single_monitoring(
                        api_key=args.api_key,
                        branch_name=args.branch,
                        file_path=args.output,
                        align_hour=args.align_hour,
                        media_dir=args.media_dir,
                    )
                except Exception as ex:
                    print(f"[!] Error tidak terduga pada siklus monitoring: {ex}")
        except KeyboardInterrupt:
            print("\n[+] Service dihentikan oleh pengguna.")
    else:
        run_single_monitoring(
            api_key=args.api_key,
            branch_name=args.branch,
            file_path=args.output,
            align_hour=args.align_hour,
            media_dir=args.media_dir,
        )


if __name__ == "__main__":
    main()
