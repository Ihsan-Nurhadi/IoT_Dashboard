# Panduan Deploy IoT Dashboard menggunakan Docker & Nginx di VPS

Dokumen ini berisi panduan langkah-demi-langkah untuk mendeploy aplikasi IoT Dashboard (Django Backend, React Frontend, Nginx Gateway, dan MQTT Worker) menggunakan Docker Compose di VPS Linux (Ubuntu/Debian).

---

## 1. Persiapan Awal di VPS

### A. Install Docker & Docker Compose
Pastikan VPS Anda sudah terinstal Docker dan Docker Compose. Jika belum, jalankan perintah berikut:
```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose-plugin

# Pastikan service Docker berjalan
sudo systemctl enable --now docker
```

### B. Clone Kode Aplikasi
Clone repository aplikasi Anda ke direktori pilihan di VPS, misalnya `/var/www/iot-dashboard`:
```bash
git clone <URL_REPOSITORY_ANDA> /var/www/iot-dashboard
cd /var/www/iot-dashboard
```

---

## 2. Konfigurasi Environment & Database (PENTING)

### A. Buat File `.env`
Buat file `.env` di direktori utama `/var/www/iot-dashboard`:
```bash
nano .env
```
Isi file dengan konfigurasi produksi Anda. Contoh:
```env
APP_PORT=3002
DEBUG=0
ALLOWED_HOSTS=IP_PUBLIK_VPS_ANDA,localhost,127.0.0.1
DJANGO_SECRET_KEY='ganti-dengan-key-produksi-yang-aman-dan-panjang'

# MQTT Config
MQTT_SERVER=broker.emqx.io
MQTT_PORT=1883
MQTT_USER=userdev
MQTT_PASSWORD=RiseDEV1989
MQTT_TOPIC_SUB=/matalite-test/in/094
MQTT_TOPIC_PUB=/matalite-test/reply/
MQTT_TOPIC_PUB2=/matalite-test/sensor/094
```

### B. Atur Hak Akses Database SQLite (Kritis untuk Docker)
Karena SQLite menyimpan database dalam bentuk file (`db.sqlite3`), Docker container memerlukan hak akses penuh untuk membaca & menulis file ini serta foldernya (karena SQLite akan membuat file journal sementara saat penulisan data).
Jalankan perintah berikut di direktori utama project di VPS:
```bash
# Berikan izin tulis ke folder backend agar Django bisa membuat file lock/journal
chmod 777 backend

# Berikan izin tulis ke file database
chmod 666 backend/db.sqlite3
```
*Catatan: Jika folder `backend/data/db.sqlite3` yang digunakan, jalankan:*
```bash
chmod 777 backend/data
chmod 666 backend/data/db.sqlite3
```

---

## 3. Jalankan OpenVPN di VPS (Split Tunneling)

Agar VPS bisa mengakses CCTV lokal tanpa memutus koneksi SSH Anda ke VPS:
1. Pindahkan file `.ovpn` ke `/etc/openvpn/client/client.conf`.
2. Edit file tersebut dan pastikan rute gateway dinonaktifkan:
   ```text
   # redirect-gateway def1
   pull-filter ignore "redirect-gateway"
   pull-filter ignore "dhcp-option DNS"
   ```
3. Aktifkan dan jalankan OpenVPN:
   ```bash
   sudo systemctl enable --now openvpn-client@client
   ```
4. Uji koneksi ke IP CCTV dari VPS:
   ```bash
   ping -c 3 10.10.4.89
   ```

---

## 4. Build & Jalankan Docker Container

Jalankan perintah Docker Compose berikut untuk melakukan build image dan menjalankan service di background:

```bash
# Build dan jalankan seluruh container
docker compose up -d --build
```

Docker Compose akan otomatis menjalankan:
1. `nms_backend` (Django API) di port internal `8000`.
2. `nms_mqtt_worker` (MQTT background listener) untuk mencatat status sensor.
3. `nms_frontend` (Nginx serving React static files) di port internal `80`.
4. `nms_nginx` (Reverse Proxy Utama) yang memetakan port `APP_PORT` (misal 3002) di VPS ke frontend dan backend.

---

## 5. Perintah Pengelolaan & Pemantauan (Troubleshooting)

### A. Melihat Logs Container
Jika ada sensor tidak merespon atau stream CCTV bermasalah, cek log masing-masing container:
```bash
# Cek semua logs
docker compose logs -f

# Cek log backend saja
docker compose logs -f backend

# Cek log MQTT worker saja
docker compose logs -f mqtt_listener
```

### B. Menghentikan Container
```bash
docker compose down
```

### C. Menerapkan Perubahan Kode Baru
Jika Anda melakukan update code (misal melakukan `git pull`):
```bash
git pull
docker compose up -d --build
```
