# 📹 Worker CCTV Gateway (RTSP & ONVIF API Bridge)

Worker ini berfungsi sebagai jembatan (API Gateway) yang mengubah stream **RTSP** dan protokol **ONVIF** dari kamera CCTV yang berada di dalam jaringan OpenVPN (`10.10.1.17`) menjadi **REST API & Live Video Stream HTTP publik**.

Dengan worker ini, Anda dan klien luar (Dashboard web, aplikasi mobile, VLC, atau pihak ketiga) dapat mengakses video dan kontrol kamera dari internet **tanpa perlu mengaktifkan VPN di perangkat masing-masing**.

---

## 🎯 Informasi Kamera Target

- **IP Kamera**: `10.10.1.17`
- **Port RTSP**: `554` (Path: `/stream1`)
- **Port ONVIF**: `2020` (Path: `/onfiv/device_service` & `/onvif/device_service`)
- **Username**: `NMSIOTYOGYA1`
- **Password**: `Nayaka2025`

---

## 🚀 Cara Menjalankan di VPS

Karena di VPS Anda **sudah terpasang dan aktif OpenVPN**, VPS dapat langsung menjangkau IP internal kamera `10.10.1.17`.

### 1. Masuk ke folder Worker_CCTV di VPS
```bash
cd /path/to/Dashboard_Ultimate_Nayaka/Worker_CCTV
```

### 2. Jalankan Container dengan Docker Compose
```bash
docker compose up -d --build
```

### 3. Periksa Log Container
```bash
docker compose logs -f
```
Jika berhasil terhubung, Anda akan melihat log:
```
[INFO] Connecting to RTSP stream: rtsp://NMSIOTYOGYA1:****@10.10.1.17:554/stream1
[INFO] RTSP stream successfully connected!
[INFO] ONVIF services successfully initialized!
[INFO] Starting CCTV API Gateway on http://0.0.0.0:3001
```

> **Catatan Firewall VPS**: Pastikan port `3001` dibuka di firewall VPS Anda (`sudo ufw allow 3001/tcp`).

---

## 🌐 Daftar Endpoint API Publik

Setelah container berjalan di VPS, seluruh endpoint berikut dapat diakses dari luar menggunakan IP VPS Anda: `http://<IP_VPS_ANDA>:3001`

### 1. Dashboard & Dokumentasi Interaktif
| Endpoint | Method | Deskripsi |
|---|---|---|
| `/` | `GET` | **Interactive Web Dashboard** dengan live player video, kontrol PTZ interaktif, status FPS, dan tombol snapshot. |
| `/docs` | `GET` | **Swagger UI** dokumentasi interaktif untuk mencoba semua endpoint langsung di browser. |
| `/redoc` | `GET` | Dokumentasi alternatif ReDoc. |

---

### 2. Live Streaming & Snapshot (RTSP ke HTTP)
| Endpoint | Method | Deskripsi & Contoh Pemakaian |
|---|---|---|
| `/api/stream` | `GET` | **Live MJPEG Video Stream**. Langsung kompatibel dengan tag HTML `<img>` tanpa plugin.<br>`<img src="http://IP_VPS:3001/api/stream" width="640" />`<br>Bisa juga dibuka di VLC Player. |
| `/api/snapshot` | `GET` | **Single JPEG Frame Snapshot** real-time resolusi penuh.<br>`fetch('http://IP_VPS:3001/api/snapshot')` |
| `/api/status` | `GET` | Status koneksi kamera, FPS terukur saat ini, resolusi, dan error trace. |
| `/api/health` | `GET` | Status kesehatan worker (`{"status": "ok"}`). |

---

### 3. ONVIF Control & REST API
| Endpoint | Method | Payload / Parameter | Deskripsi |
|---|---|---|---|
| `/api/onvif/device-info` | `GET` | - | Mengambil Manufacturer, Model, Firmware, Serial Number. |
| `/api/onvif/profiles` | `GET` | - | Daftar profil video encoding dari kamera. |
| `/api/onvif/stream-uri` | `GET` | `?profile_token=...` (opsional) | Mendapatkan URI RTSP resmi dari ONVIF. |
| `/api/onvif/snapshot-uri` | `GET` | `?profile_token=...` (opsional) | Mendapatkan URI snapshot HTTP dari ONVIF. |
| `/api/onvif/ptz/move` | `POST` | `{"pan": 0.5, "tilt": 0.0, "zoom": 0.0}` | Menggerakkan kamera (Continuous Move) dengan kecepatan -1.0 s/d 1.0. |
| `/api/onvif/ptz/stop` | `POST` | `{}` | Menghentikan pergerakan kamera PTZ seketika. |
| `/api/onvif/ptz/presets` | `GET` | - | Mengambil daftar preset posisi PTZ yang tersimpan di kamera. |
| `/api/onvif/ptz/goto-preset` | `POST` | `{"preset_token": "1"}` | Mengarahkan posisi kamera ke preset tertentu. |

---

### 4. Transparent ONVIF SOAP Proxy
| Endpoint | Method | Deskripsi |
|---|---|---|
| `/onvif/{service}` | `POST` | Meneruskan permintaan SOAP XML standar ONVIF langsung ke port 2020 kamera.<br>Memungkinkan software VMS eksternal (seperti ONVIF Device Manager, Synology Surveillance) terhubung ke `http://IP_VPS:3001` tanpa VPN. |

---

## ⚙️ Variabel Konfigurasi (`.env`)

| Variabel | Default | Keterangan |
|---|---|---|
| `GATEWAY_PORT` | `3001` | Port publik yang dibuka di VPS untuk API Gateway |
| `CAMERA_HOST` | `10.10.1.17` | IP internal kamera CCTV (didapat dari VPN) |
| `CAMERA_USER` | `NMSIOTYOGYA1` | Username kamera |
| `CAMERA_PASS` | `Nayaka2025` | Password kamera |
| `RTSP_PORT` | `554` | Port RTSP kamera |
| `RTSP_PATH` | `/stream1` | Stream channel kamera |
| `ONVIF_PORT` | `2020` | Port layanan ONVIF kamera |
| `ONVIF_PATH` | `/onfiv/device_service` | Path endpoint ONVIF |
| `TARGET_FPS` | `20` | Target frame per second untuk stream web |
| `STREAM_WIDTH` | `1280` | Batas resolusi lebar (resize) demi efisiensi bandwidth |
| `STREAM_QUALITY` | `75` | Kualitas kompresi JPEG (1 - 100) |

---

## 🔧 Integrasi ke Frontend React Dashboard

Jika Anda ingin menampilkan live stream CCTV ini di komponen React Dashboard Anda:

```jsx
// Cukup pasang tag <img> biasa tanpa library RTSP rumit:
<img 
  src="http://IP_VPS:3001/api/stream" 
  alt="Live CCTV Pos 17" 
  style={{ width: '100%', borderRadius: '12px' }} 
/>
```

Dan untuk menggerakkan kamera lewat tombol React:
```javascript
async function panLeft() {
  await fetch('http://IP_VPS:3001/api/onvif/ptz/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pan: -0.5, tilt: 0, zoom: 0 })
  });
}

async function stopCamera() {
  await fetch('http://IP_VPS:3001/api/onvif/ptz/stop', { method: 'POST' });
}
```
