"""
MaiView / Nayaka Auto-Degrade Watcher for Fatigue Sites (24/7 VPS Daemon)
========================================================================
Deskripsi:
- Memantau status online/offline 61 site fatigue Mitratel secara real-time.
- Ketika site terdeteksi OFFLINE, script otomatis memicu payload DEGRADE ke server
  agar site tetap terlihat aman/online di dashboard monitoring pengguna.
- Melakukan pembaruan (re-degrade) secara berkala (misal tiap 15 menit) selama site
  masih berstatus offline.
- Ketika site kembali ONLINE (telemetri asli masuk), status degrade otomatis di-reset.
- Kredensial username dan password dimuat aman melalui environment file (.env).
- Dirancang untuk berjalan non-stop (24/7) di VPS (mendukung Systemd & Docker).
"""

import argparse
from datetime import datetime, timezone, timedelta
import json
import os
import re
import sys
import time
import urllib3
import requests

# Pastikan output konsol langsung ter-flush (berguna untuk systemd / docker logs)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    except Exception:
        pass

# Nonaktifkan warning SSL jika endpoint menggunakan sertifikat internal / proxy
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# FALLBACK & DOTENV LOADER
# ==============================================================================
def load_env_file(filepath: str = None):
    """
    Memuat variabel dari file .env secara otomatis.
    Mendukung library python-dotenv jika tersedia, atau parser bawaan sebagai fallback.
    """
    candidates = [
        filepath,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
    ]
    env_path = None
    for p in candidates:
        if p and os.path.exists(p):
            env_path = p
            break

    if not env_path:
        return

    # Coba gunakan python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass

    # Parser fallback manual jika python-dotenv belum terinstall
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"[!] Warning gagal memuat {env_path}: {e}")


# Muat environment variables sekarang
load_env_file()

# ==============================================================================
# KONFIGURASI DARI ENVIRONMENT VARIABLES (.env)
# ==============================================================================
# Kredensial Login Dashboard Nayaka / MaiView
DEFAULT_USERNAME = os.getenv("DEGRADE_USERNAME", os.getenv("DASHBOARD_USERNAME", ""))
DEFAULT_PASSWORD = os.getenv("DEGRADE_PASSWORD", os.getenv("DASHBOARD_PASSWORD", ""))

# Endpoint Login Dashboard
LOGIN_URL = os.getenv("DEGRADE_LOGIN_URL", "https://admin.nayakanms.com/api/auth/login")

# Public API untuk memonitor status online/offline site
PUBLIC_API_URL = os.getenv("DEGRADE_PUBLIC_API_URL", "https://api.maiviewmitratel.id/v1/sites")
PUBLIC_API_KEY = os.getenv(
    "DEGRADE_PUBLIC_API_KEY",
    "nms_live_0c05c2b6_d09b6897332bcc9fde952de761b6e15ba8cb9366817b22231ca126a2b933106a"
)

# Endpoint Degrade Web Dashboard (Override opsional)
DEGRADE_URL_OVERRIDE = os.getenv("DEGRADE_URL_OVERRIDE", None)

# Alasan Degrade default
DEFAULT_REASON = os.getenv("DEGRADE_REASON", "-")

# Interval pengecekan status (detik, default 30 detik)
CHECK_INTERVAL_SECONDS = int(os.getenv("DEGRADE_CHECK_INTERVAL", "30"))

# Interval pengiriman ulang degrade berkala jika site masih offline (menit, default 15 menit)
RE_DEGRADE_INTERVAL_MINUTES = int(os.getenv("DEGRADE_RE_DEGRADE_MINUTES", "15"))

WIB = timezone(timedelta(hours=7))

# ==============================================================================
# FALLBACK DAFTAR 61 SITE FATIGUE MITRATEL (UUID : NAMA SITE)
# ==============================================================================
DEFAULT_WATCHLIST_61_SITES = {
    "31e1943e-0cb8-4c49-bf31-64351986792b": "PEDURENANMUSTIKAJAYA (CKR-04-181)",
    "661cc75b-37ec-539d-9197-853f91dd7f16": "JALANMUSTIKASARI (BKS-04-079)",
    "0d44de3d-f9b8-4ff1-ad1a-5c67049bb9b4": "SMU84 (GGP-04-196)",
    "59b20bcc-9820-4ca4-9b4e-00ea5710821e": "SWADAYA (CKG-04-367)",
    "278e6842-95f5-458a-bbfa-197c296cecc5": "BEKASI_KOTA (BKS-04-194)",
    "12fbe987-0b5c-4876-907d-5a9fc27263c9": "GANGAMBONTANGERANG (TNG-04-080)",
    "9f4640dc-6a3f-561b-9d41-45d2f6fefd1a": "PERMANENISASICIOKONGSUKARESIKSIDAMULIH (CMS-05-279)",
    "6eef5647-3806-5a41-b4d6-0e194cf269f8": "KERTAMUKTI-CIKONDANG (SPA-05-017)",
    "8ee66d3a-18f6-59bf-a2df-94bf7102e3b3": "JLABDULSALEH-SETIARATUTSK (TSM-05-022)",
    "60be78c0-827c-50bc-ab9b-c405a2e58ff5": "BANTARSARI-CIEUNTEUNG (BDG-05-625)",
    "b3cbeea5-c726-538d-8c44-d8ef5385fb62": "Jalan Anggrek Siitu (SMD-05-035)",
    "d0e14a1a-3ec6-5ce4-b15c-3a3d5e2361b9": "Rnc_Karmul2_part2_Site Planning 1_NewSite_120 (SPA-05-085)",
    "efc8c119-e5a0-56aa-bcf4-60dd185fb48f": "Karangboyo Cepu (BLA-06-015)",
    "0f89a9f2-23c2-5e43-85e7-2b3eeff251b6": "Karangjati Indah (BTL-06-034)",
    "2219b1aa-b2b9-5095-8b8a-b8e7343e52e4": "PASIR KIDUL BANYUMAS (PWT-06-046)",
    "fb2f00a4-79fc-5c21-b3b4-84ae34ec8116": "PODOSUGIH (PKL-06-025)",
    "0989f5c4-a5ff-5100-9884-601446e5ca93": "BANJARSARI_PEDALANGAN (SMG-06-366)",
    "19e917d2-38ae-5a7a-8f4b-2d7c0413ba11": "Letjend S Parman Ungaran (CLP-06-058)",
    "48a8eb6a-4933-5c02-bf88-b2efce86d5c3": "Palebon tengah (BYL-06-122)",
    "3f3a8bca-f033-5f00-8848-b4b0e8b2cefc": "MARGODADI (SMN-06-114)",
    "9d5483eb-2746-51f1-a1e0-63ce79c65691": "GanggangPanjang (SDA-07-036)",
    "a66e4a87-320c-535d-a602-53b49e29a39f": "MANGUNSARKORO 3 (TRK-07-024)",
    "be0572b6-ec62-588d-bb34-2e92c274ee79": "GAYUNG_SARI_BARAT-JAMBANGAN (SBY-07-645)",
    "a1cae5e7-aa98-5c05-b045-f09b537f005c": "SEPANDECANDI2DMT (SDA-07-078)",
    "78479e97-28d8-55df-9d77-d40bf59fc544": "BUKITRAYASEPAKU (PNJ-09-044)",
    "bd3deb2d-6e81-5540-9eed-04fd397d5ca6": "DMT_NEW_IKN (PNJ-09-036)",
    "83a838ed-698f-414a-a37c-5669f5a1e4b6": "DMT ISAT_Tamangapa (SULAWESI)",
    "4c74031d-b6a8-500b-ba85-f2d0119e76fa": "Al Yusro PKP (PGP-03-007)",
    "bc422425-bbc3-407c-b3a3-6b1240504b6f": "Perumnas Salemba (PGP-03-054)",
    "8936082c-497d-5a9f-a89e-26f5b991da71": "GIRIMAYA (PGP-03-059)",
    "601362e5-fe70-5b32-a5d0-be16c3539fcb": "Suak Permai (PLG-03-010)",
    "6fcb2751-2ef3-5bc4-b81b-568d277d5490": "SUKA MULYA PLG (PLG-03-096)",
    "ef317e08-9df5-5716-b183-b09e075073e5": "Keluarga PLG (PLG-03-106)",
    "fa8b6602-30f9-4b50-bd7f-32392e26b4d0": "Lubuk Kawah PLG (PLG-03-107)",
    "0c19df39-014c-535d-b0aa-5ea5be5eb126": "Arimbi PLG (PLG-03-108)",
    "f186fa5b-7b0b-53c4-90ef-8fe9d4793f77": "Jalan BSD PLG (PLG-03-109)",
    "60c6d997-7505-59fe-924e-b5f7b0ceb2a7": "Jalan Jepang PLG (PLG-03-112)",
    "3fe38779-7a32-55eb-a558-75b8a531cf5c": "Gaya Baru PLG (PLG-03-118)",
    "475d4a67-27b9-56e6-99eb-035df9039e14": "Lorong Pancasila PLG (PLG-03-120)",
    "129e160e-8628-5421-9538-4e0e5ea4e414": "Sentosa 2 PLG (PLG-03-121)",
    "8c54f2e5-0898-4333-addd-62a8c80a8704": "16 Ulu PLG (PLG-03-128)",
    "72044fe7-f9b8-5cf7-b2eb-6f4eb273f080": "Lorong Depok PLG (PLG-03-131)",
    "26610332-9599-5ea8-97ba-964fa93c0ee0": "Mataram Kertapati (PLG-03-132)",
    "d7722749-366d-5511-bdc1-ca414b437e29": "KOMPLEK_PMD-SEDUDUK_PUTIH (PLG-03-387)",
    "da9e17b8-15a0-54ec-a633-8ea87e793081": "SUKABANGUN2 (PLG-03-398)",
    "5d4b9619-3db6-5b72-b75a-6a581e285d82": "Ketuan Jaya (PLG-03-040)",
    "8a0ce123-5755-520e-8a19-da49544a059b": "PEMBANGUNAN BDL (BDL-03-064)",
    "6b68e0d6-1d37-5800-8eeb-1188448ebf57": "SIMPANG TALUAK (PBR-02-482)",
    "0b9b36ea-1d8f-51ba-b2c6-eaef779fa03b": "PARIAMAN 6 (BTM-02-493)",
    "ecba8564-28b7-5428-a476-ebce22588c83": "DESA_HARAPAN (BLS-02-175)",
    "e974e4fe-4869-52e4-9669-e61a6b0c2a86": "DUMAI 9 (DUM-02-037)",
    "d01e4a13-39ca-5ca3-a55e-2fca213bf9cf": "BSK 3 (BSK-02-015)",
    "21bc36ef-59df-5205-8716-1f6b1580ca02": "Lenggini 3 (BKN-02-035)",
    "2492e0b8-26f0-488e-a3a1-7652ed6c65a8": "SMAS CENDANA (BLS-02-054)",
    "a61da59f-d3ec-5807-b71d-dd5f25785bb5": "Sudirman Bengkalis (BLS-02-056)",
    "4d88e72f-5b65-5cce-bd28-091f34ff24ec": "Raden Patah (reloc) (BTM-02-114)",
    "ea3295c3-1ffb-5b58-94ce-a9796ff012aa": "PADANG PASIR POI (PAD-02-092)",
    "ec1cf614-7cf6-53d9-a477-9df030df7c8d": "GANTING PARAK 2 (PAD-02-091)",
    "e8992e5c-7d9a-58f6-9f0a-660cba7df607": "Dagang Kelambir (LBP-01-128)",
    "c8a1498b-7032-5bf5-bb1b-3b4df9d1cf26": "PELAB AJIBATA (PRR-01-004)",
    "9c759535-c335-502a-9e32-a589cf879d71": "Komplek Sejahtera (MDN-01-097)",
}


def load_watchlist_sites(filter_targets: list[str] = None) -> dict[str, str]:
    """
    Memuat daftar site yang diawasi (UUID -> Nama/Kode).
    Sumber utama: sites_mitratel.json.
    - Setiap site yang memiliki field 'uuid' (tidak kosong) akan DIAWASI.
    - Jika Anda ingin MENGHAPUS / MELEWATI suatu site dari monitoring,
      cukup KOSONGKAN atau HAPUS baris "uuid" pada site tersebut di sites_mitratel.json!
    """
    watchlist = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Prioritas Utama: sites_mitratel.json
    sites_mitratel_paths = [
        os.path.join(base_dir, "sites_mitratel.json"),
        os.path.join(os.getcwd(), "sites_mitratel.json"),
        "/app/sites_mitratel.json",
    ]
    for p in sites_mitratel_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    if isinstance(items, list):
                        for it in items:
                            uid = str(it.get("uuid") or "").strip()
                            if uid:  # Hanya masukkan site yang memiliki UUID valid
                                site_code = it.get("site_id", "")
                                name = it.get("name", "")
                                watchlist[uid] = f"{name} ({site_code})"
                if watchlist or items:
                    print(f"[*] Berhasil memuat watchlist dari: {os.path.basename(p)} ({len(watchlist)} site dengan UUID aktif)")
                    break
            except Exception as e:
                print(f"[!] Warning membaca {p}: {e}")

    # Fallback darurat jika sites_mitratel.json sama sekali tidak ditemukan
    if not watchlist:
        print("[!] File sites_mitratel.json tidak ditemukan atau kosong, menggunakan daftar bawaan.")
        watchlist = dict(DEFAULT_WATCHLIST_61_SITES)

    # Filter tambahan jika ditentukan via argumen CLI (--target) atau ENV (DEGRADE_TARGET_SITES)
    if filter_targets:
        clean_targets = [t.strip().upper() for t in filter_targets if t.strip()]
        filtered = {}
        for uid, name in watchlist.items():
            name_upper = name.upper()
            uid_upper = uid.upper()
            if any(tgt in name_upper or tgt == uid_upper for tgt in clean_targets):
                filtered[uid] = name
        return filtered if filtered else watchlist

    return watchlist
    if filter_targets:
        clean_targets = [t.strip().upper() for t in filter_targets if t.strip()]
        filtered = {}
        for uid, name in watchlist.items():
            name_upper = name.upper()
            uid_upper = uid.upper()
            if any(tgt in name_upper or tgt == uid_upper for tgt in clean_targets):
                filtered[uid] = name
        return filtered if filtered else watchlist

    return watchlist


def sync_sites_from_api(api_key: str = PUBLIC_API_KEY) -> bool:
    """
    Sinkronisasi otomatis: mengambil daftar seluruh site dari Public API
    dan mencocokkannya dengan sites_mitratel.json, lalu memperbarui sites_degrade_watchlist.json.
    """
    print("[*] Melakukan sinkronisasi site langsung dari Public API...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, "sites_mitratel.json")
    if not os.path.exists(local_path):
        print(f"[!] File {local_path} tidak ditemukan untuk dicocokkan.")
        return False

    with open(local_path, "r", encoding="utf-8") as f:
        local_sites = json.load(f)

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key.replace('Bearer ', '').strip()}",
        "User-Agent": "AutoDegrade-Sync/1.0",
    }

    all_api_sites = []
    page = 1
    while True:
        try:
            r = requests.get(f"{PUBLIC_API_URL}?page={page}&per_page=100", headers=headers, timeout=15)
            if r.status_code != 200:
                print(f"[!] Gagal fetch halaman {page}: HTTP {r.status_code}")
                break
            res = r.json()
            data = res.get("data", [])
            if not data:
                break
            all_api_sites.extend(data)
            pagination = res.get("pagination", {})
            total_pages = pagination.get("total_pages", 1)
            print(f"    • Halaman {page}/{total_pages} terambil ({len(all_api_sites)} site terakumulasi)")
            if page >= total_pages:
                break
            page += 1
        except Exception as e:
            print(f"[!] Error saat sync API: {e}")
            break

    def norm(text):
        return re.sub(r"[^a-zA-Z0-9]", "", str(text or "")).upper()

    watchlist_dict = {}
    watchlist_list = []
    matched_count = 0

    for item in local_sites:
        no = item.get("no")
        ls_id = item.get("site_id", "")
        ls_name = item.get("name", "")
        norm_id = norm(ls_id)
        norm_name = norm(ls_name)

        found = None
        for a in all_api_sites:
            as_code = norm(a.get("site_code"))
            as_name = norm(a.get("name"))
            if (norm_id and (norm_id == as_code or norm_id == as_name)) or (norm_name and (norm_name == as_code or norm_name == as_name)):
                found = a
                break

        if found:
            matched_count += 1
            uid = found["id"]
            display_name = f"{ls_name} ({ls_id})"
            watchlist_dict[uid] = display_name
            watchlist_list.append({
                "no": no,
                "id": uid,
                "site_code": ls_id,
                "name": ls_name,
                "branch": found.get("branch_name", "Mitratel Default"),
                "last_known_status": found.get("status", "unknown")
            })
            item["uuid"] = uid

    out_file = os.path.join(base_dir, "sites_degrade_watchlist.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total": len(watchlist_list), "sites": watchlist_list, "map": watchlist_dict}, f, indent=2)

    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(local_sites, f, indent=2)

    print(f"[+] Sinkronisasi Selesai! Berhasil mencocokkan {matched_count}/{len(local_sites)} site.")
    print(f"[+] Hasil disimpan ke {out_file}\n")
    return True


# ==============================================================================
# AUTHENTICATION MANAGER (AUTO-LOGIN 24/7 & AUTO-REFRESH)
# ==============================================================================
class AuthManager:
    """Mengelola token otentikasi login, termasuk refresh token otomatis jika expired."""

    def __init__(self, username: str = "", password: str = "", static_token: str = "", cookie: str = ""):
        self.username = username
        self.password = password
        self.current_token = static_token
        self.cookie = cookie
        self.login_url = LOGIN_URL
        self.session = requests.Session()

    def login(self) -> bool:
        """Melakukan login ke endpoint autentikasi dan menyimpan token JWT baru."""
        if not self.username or not self.password:
            return False

        now_str = datetime.now(WIB).strftime("%H:%M:%S")
        print(f"[{now_str} WIB] [*] Melakukan autentikasi login sebagai '{self.username}'...")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoDegradeWatcher/2.0",
        }
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            res = self.session.post(self.login_url, headers=headers, json=payload, timeout=12, verify=False)
            if res.status_code == 200:
                data = res.json()
                token = (
                    data.get("token")
                    or (data.get("data", {}) if isinstance(data.get("data"), dict) else {}).get("token")
                    or (data.get("data", {}) if isinstance(data.get("data"), dict) else {}).get("access_token")
                    or data.get("access_token")
                )
                if token:
                    self.current_token = token
                    print(f"[{now_str} WIB] [+] Login Berhasil! Token JWT baru berhasil diperoleh.")
                    return True
                else:
                    print(f"[{now_str} WIB] [!] Login respon 200 tetapi format token tidak dikenali: {res.text[:140]}")
            elif res.status_code in (401, 403):
                print(f"[{now_str} WIB] [!] Gagal Login: Username atau Password salah (HTTP {res.status_code}).")
            else:
                print(f"[{now_str} WIB] [!] Gagal Login: HTTP {res.status_code} ({res.text[:140]})")
        except Exception as e:
            print(f"[{now_str} WIB] [!] Error koneksi ke endpoint login: {e}")

        return False

    def get_token(self) -> str:
        """Mengambil token yang sedang aktif. Jika belum ada, mencoba login."""
        if not self.current_token and self.username and self.password:
            self.login()
        return self.current_token

    def handle_expired(self) -> bool:
        """Dipanggil saat server menolak dengan HTTP 401 (token expired)."""
        now_str = datetime.now(WIB).strftime("%H:%M:%S")
        print(f"[{now_str} WIB] [!] Token terdeteksi kadaluarsa. Memperbarui token otomatis melalui re-login...")
        self.current_token = ""
        return self.login()


# ==============================================================================
# MONITORING STATUS & TRIGGER DEGRADE
# ==============================================================================
def get_site_status(session: requests.Session, site_id: str, api_key: str = PUBLIC_API_KEY) -> dict | None:
    """Mengambil status terkini site dari Public API menggunakan session pool."""
    url = f"{PUBLIC_API_URL}/{site_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key.replace('Bearer ', '').strip()}",
        "User-Agent": "AutoDegrade-Watcher/2.0",
    }
    try:
        res = session.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            return res.json().get("data")
        elif res.status_code == 404:
            return None
        else:
            return None
    except requests.exceptions.RequestException:
        return None
    except Exception:
        return None


def trigger_degrade_site(
    session: requests.Session,
    site_id: str,
    auth_mgr: AuthManager,
    degrade_url: str = None,
    reason: str = DEFAULT_REASON,
) -> bool:
    """
    Mengirim perintah HTTP POST ke endpoint internal untuk men-degrade site.
    Mendukung auto-relogin jika token expired (HTTP 401).
    """
    candidate_urls = [
        degrade_url.replace("{site_id}", site_id) if (degrade_url and "{site_id}" in degrade_url) else degrade_url,
        f"https://admin.nayakanms.com/api/admin/sites/{site_id}/degrade",
        f"https://maiviewmitratel.id/api/v1/sites/{site_id}/degrade",
        f"https://admin.nayakanms.com/api/v1/sites/{site_id}/degrade",
    ]
    target_urls = [u for u in candidate_urls if u]

    for attempt in range(2):
        token = auth_mgr.get_token()
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AutoDegradeWatcher/2.0",
        }
        if token:
            clean_token = token.replace("Bearer ", "").replace("bearer ", "").strip()
            headers["Authorization"] = f"Bearer {clean_token}"
        if auth_mgr.cookie:
            headers["Cookie"] = auth_mgr.cookie

        payload = {
            "reason": reason,
            "site_id": site_id,
        }

        for url in target_urls:
            try:
                res = session.post(url, headers=headers, json=payload, timeout=10, verify=False)
                if res.status_code in (200, 201):
                    try:
                        res_json = res.json()
                        msg = res_json.get("message", "Success")
                        print(f"    [+] Respon Server ({url}): {msg}")
                    except Exception:
                        print(f"    [+] Berhasil HTTP {res.status_code}")
                    return True
                elif res.status_code in (401, 403):
                    if attempt == 0 and auth_mgr.username and auth_mgr.password:
                        if auth_mgr.handle_expired():
                            break  # ulangi putaran berikutnya dengan token baru
                    print(f"    [!] Error Otentikasi HTTP {res.status_code} pada {url}")
                else:
                    if res.status_code != 404:
                        print(f"    [!] Server merespon: HTTP {res.status_code} ({res.text[:120]})")
            except Exception:
                pass

    return False


# ==============================================================================
# WATCHER ENGINE (LOOP UTAMA 24/7)
# ==============================================================================
def run_watcher(
    watchlist: dict,
    auth_mgr: AuthManager,
    api_key: str,
    degrade_endpoint: str = None,
    reason: str = DEFAULT_REASON,
    interval: int = CHECK_INTERVAL_SECONDS,
    re_degrade_interval_minutes: int = RE_DEGRADE_INTERVAL_MINUTES,
):
    """
    Loop utama pemantau site fatigue yang bekerja terus-menerus 24/7 di latar belakang.
    """
    re_degrade_interval_sec = max(60, re_degrade_interval_minutes * 60)

    print("=" * 80)
    print(f"{'MAIVIEW / NAYAKA AUTO-DEGRADE WATCHER (24/7 VPS SERVICE)':^80}")
    print("=" * 80)
    print(f"[*] Total Site Dipantau     : {len(watchlist)} site")
    print(f"[*] Interval Pengecekan     : Setiap {interval} detik")
    print(f"[*] Re-Degrade Berkala      : Setiap {re_degrade_interval_minutes} menit (jika site tetap offline)")
    print(f"[*] Alasan Degrade          : \"{reason}\"")
    print(f"[*] Mode Autentikasi        : {'Auto-Login (Kredensial dari .env)' if auth_mgr.username else 'Token Statis / Tamu'}")
    print(f"[*] Status Watcher          : AKTIF. Tekan Ctrl+C untuk berhenti.\n" + "-" * 80)

    # Inisialisasi login awal
    if auth_mgr.username and not auth_mgr.current_token:
        auth_mgr.login()

    # Session persistent untuk connection pooling & performa optimal
    session = requests.Session()

    # State tracking: {site_id: {"last_status": str, "is_degraded": bool, "last_degraded_time": float}}
    site_states = {
        sid: {"last_status": "UNKNOWN", "is_degraded": False, "last_degraded_time": 0.0}
        for sid in watchlist
    }

    try:
        while True:
            cycle_start = time.time()
            now_dt = datetime.now(WIB)
            now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

            online_count = 0
            offline_degraded_count = 0
            offline_new_count = 0
            err_count = 0

            for site_id, site_name in watchlist.items():
                data = get_site_status(session, site_id, api_key=api_key)
                if not data:
                    err_count += 1
                    continue

                current_status = str(data.get("status", "unknown")).lower()
                state = site_states[site_id]
                prev_status = state["last_status"]

                # 1. KONDISI A: Site Hidup (Online via MQTT)
                if current_status == "online":
                    online_count += 1
                    if prev_status != "online":
                        print(f"[{now_str} WIB] [PULIH] [{site_name}] Status kembali ONLINE (Data telemetri masuk).")
                        state["is_degraded"] = False
                        state["last_degraded_time"] = 0.0
                    state["last_status"] = "online"

                # 2. KONDISI B: Site Mati (Offline)
                elif current_status == "offline":
                    state["last_status"] = "offline"

                    # Kasus B.1: Baru pertama kali offline
                    if not state["is_degraded"]:
                        offline_new_count += 1
                        print(f"[{now_str} WIB] [PERINGATAN] [{site_name}] Terdeteksi OFFLINE! Mengirim perintah Degrade...")
                        success = trigger_degrade_site(
                            session=session,
                            site_id=site_id,
                            auth_mgr=auth_mgr,
                            degrade_url=degrade_endpoint,
                            reason=reason,
                        )
                        if success:
                            state["is_degraded"] = True
                            state["last_degraded_time"] = time.time()
                            offline_degraded_count += 1
                            print(f"    [OK] [{site_name}] Berhasil di-DEGRADE otomatis! Site aman di dashboard.")
                        else:
                            print(f"    [GAGAL] [{site_name}] Tidak dapat mengirim degrade.")

                    # Kasus B.2: Sudah degraded, cek apakah waktunya kirim degrade ulang secara berkala
                    else:
                        offline_degraded_count += 1
                        elapsed_since_degrade = time.time() - state["last_degraded_time"]
                        if elapsed_since_degrade >= re_degrade_interval_sec:
                            print(f"[{now_str} WIB] [BERKALA] [{site_name}] Masih OFFLINE ({round(elapsed_since_degrade/60, 1)}m). Memperbarui status Degrade...")
                            success = trigger_degrade_site(
                                session=session,
                                site_id=site_id,
                                auth_mgr=auth_mgr,
                                degrade_url=degrade_endpoint,
                                reason=reason,
                            )
                            if success:
                                state["last_degraded_time"] = time.time()
                                print(f"    [OK] [{site_name}] Payload Degrade berkala berhasil diperbarui.")

                # Delay sangat kecil antar request untuk kelancaran koneksi
                time.sleep(0.04)

            # Cetak ringkasan heartbeat berkala satu baris yang bersih
            summary_parts = [
                f"{len(watchlist)} Site dipantau",
                f"{online_count} Online",
                f"{offline_degraded_count} Degraded (Aman)",
            ]
            if offline_new_count > 0:
                summary_parts.append(f"{offline_new_count} Baru Degrade")
            if err_count > 0:
                summary_parts.append(f"{err_count} API Timeout")

            print(f"[{now_str} WIB] [Pengecekan Rutin] {' | '.join(summary_parts)}")

            # Hitung waktu tidur presisi agar pas interval detik
            cycle_elapsed = time.time() - cycle_start
            sleep_duration = max(1.0, interval - cycle_elapsed)
            time.sleep(sleep_duration)

    except KeyboardInterrupt:
        print("\n[+] Watcher dihentikan oleh pengguna.")


# ==============================================================================
# MAIN ENTRYPOINT & CLI PARSER
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Script Autodegrade 24/7 untuk memantau seluruh site fatigue di MaiView / Nayaka NMS."
    )
    parser.add_argument(
        "--env-file",
        help="Path ke file .env kustom.",
    )
    parser.add_argument(
        "--username",
        "-u",
        default=DEFAULT_USERNAME,
        help="Username / Email akun Dashboard Nayaka/MaiView untuk Auto-Login (default: dari .env).",
    )
    parser.add_argument(
        "--password",
        "-p",
        default=DEFAULT_PASSWORD,
        help="Password akun Dashboard Nayaka/MaiView untuk Auto-Login (default: dari .env).",
    )
    parser.add_argument(
        "--token",
        "-t",
        default="",
        help="Bearer Token JWT jika ingin menggunakan token statis langsung.",
    )
    parser.add_argument(
        "--cookie",
        "-c",
        default="",
        help="Cookie sesi browser jika menggunakan session cookie.",
    )
    parser.add_argument(
        "--url",
        help="URL endpoint degrade lengkap (opsional, jika ingin override URL).",
    )
    parser.add_argument(
        "--reason",
        "-r",
        default=DEFAULT_REASON,
        help=f"Alasan degrade (default: '{DEFAULT_REASON}').",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=CHECK_INTERVAL_SECONDS,
        help=f"Interval pengecekan dalam detik (default: {CHECK_INTERVAL_SECONDS}s).",
    )
    parser.add_argument(
        "--re-degrade-min",
        type=int,
        default=RE_DEGRADE_INTERVAL_MINUTES,
        help=f"Interval pengiriman ulang degrade berkala dalam menit (default: {RE_DEGRADE_INTERVAL_MINUTES}m).",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        default=PUBLIC_API_KEY,
        help="Public API Key untuk pengecekan status site.",
    )
    parser.add_argument(
        "--target",
        help="Filter hanya site tertentu yang diawasi (pisahkan koma UUID / Site Code).",
    )
    parser.add_argument(
        "--sync-sites",
        action="store_true",
        help="Lakukan sinkronisasi daftar site langsung dari Public API sebelum memulai monitoring.",
    )

    args = parser.parse_args()

    # Muat environment file jika ditentukan di argumen
    if args.env_file:
        load_env_file(args.env_file)

    if args.sync_sites:
        sync_sites_from_api(api_key=args.api_key or PUBLIC_API_KEY)

    username = args.username or os.getenv("DEGRADE_USERNAME", "")
    password = args.password or os.getenv("DEGRADE_PASSWORD", "")
    target_filter = args.target.split(",") if args.target else os.getenv("DEGRADE_TARGET_SITES", "").split(",")
    target_filter = [t.strip() for t in target_filter if t.strip()]

    # Muat seluruh site yang diawasi (61 site default)
    watchlist = load_watchlist_sites(filter_targets=target_filter if target_filter else None)

    if not username and not args.token and not args.cookie:
        print("[!] PERINGATAN: Kredensial login belum dikonfigurasi di file .env!")
        print("    Silakan buka file 'Worker_Verticality/.env' lalu isi:")
        print("    DEGRADE_USERNAME=akun_anda")
        print("    DEGRADE_PASSWORD=password_anda\n")

    auth_mgr = AuthManager(
        username=username,
        password=password,
        static_token=args.token,
        cookie=args.cookie,
    )

    run_watcher(
        watchlist=watchlist,
        auth_mgr=auth_mgr,
        api_key=args.api_key or PUBLIC_API_KEY,
        degrade_endpoint=args.url or DEGRADE_URL_OVERRIDE,
        reason=args.reason or DEFAULT_REASON,
        interval=args.interval or CHECK_INTERVAL_SECONDS,
        re_degrade_interval_minutes=args.re_degrade_min or RE_DEGRADE_INTERVAL_MINUTES,
    )


if __name__ == "__main__":
    main()
