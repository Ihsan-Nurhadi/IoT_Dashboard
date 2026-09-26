# ESP32 Verticality Simulator - Docker Deployment Guide

Modul ini telah di-unified agar **seluruh device simulator (21 device atau lebih) dapat berjalan bersamaan dalam 1 Docker Image & 1 Container yang sangat ringan** (menggunakan multi-threading, konsumsi RAM hanya ~25-45MB) dengan fitur **Auto-Reconnect & Supervisor Watchdog** agar tidak pernah mati/macet di VPS.

---

## 🛡️ Fitur Ketahanan (Fault Tolerance & Auto-Recovery)
1. **Thread Supervisor / Watchdog**: Thread utama terus memonitor status ke-21 worker thread setiap 5 detik. Jika ada thread yang terhenti karena crash/error socket tak terduga, supervisor otomatis menghidupkannya kembali (*auto-restart*).
2. **Infinite Auto-Reconnect**: Jika broker EMQX restart atau jaringan VPS berkedip, worker tidak akan exit. Worker akan terus mencoba menyambung ulang (*retry loop*) secara otomatis.
3. **Stale Connection Reset**: Jika koneksi terdeteksi macet (>120s tanpa publish), client MQTT otomatis di-reinisialisasi.
4. **Docker Healthcheck**: Memantau file detak jantung `/tmp/worker_alive`. Jika seluruh proses Python freeze, Docker otomatis me-restart container (`restart: always`).

## 📁 Struktur File
- **`devices.json`**: Daftar 11 device (CHIP_ID & MAC_ADDRESS). Jika ada device baru, cukup tambahkan di sini tanpa edit kode Python.
- **`runner.py`**: Entrypoint utama yang mengelola thread untuk seluruh simulator.
- **`Dockerfile`**: Image Python 3.10-slim ringan (~150MB).
- **`docker-compose.yml`**: Compose file mandiri (standalone) di dalam folder ini.
- **`simulator_vertical*.py`**: Script asli (tetap dipertahankan untuk kebutuhan manual/lokal).

---

## 🚀 Cara Menjalankan di VPS

### Opsi 1: Menjalankan Bersama Dashboard Utama (Direkomendasikan)
Service `verticality_simulators` sudah ditambahkan ke root `docker-compose.yml`.

Di root folder proyek (`Dashboard_Ultimate_Nayaka`):
```bash
docker compose up -d --build verticality_simulators
```

Untuk melihat log simulator:
```bash
docker compose logs -f verticality_simulators
```

---

### Opsi 2: Menjalankan Standalone di Folder Worker_Verticality
Jika ingin menjalankan simulator secara terpisah di VPS atau server lain:

Masuk ke folder `Worker_Verticality`:
```bash
cd Worker_Verticality
docker compose up -d --build
```

Melihat log:
```bash
docker compose logs -f
```

Menghentikan:
```bash
docker compose down
```

---

### Opsi 3: Menjalankan 1 Device Tertentu Saja (Single Device Mode)
Jika suatu saat Anda hanya ingin menjalankan 1 device tertentu dari image yang sama, cukup oper environment variable `CHIP_ID` dan `MAC_ADDRESS`:

```bash
docker run -d --name worker_swadaya \
  -e CHIP_ID="E32_VER_SWADAYA" \
  -e MAC_ADDRESS="3A:0E:4C:1E:80:6E" \
  nms_verticality_workers
```

Atau menggunakan filter `TARGET_CHIPS` untuk menjalankan subset device:
```bash
docker run -d --name worker_subset \
  -e TARGET_CHIPS="E32_VER_SWADAYA,E32_VER_SMU84" \
  nms_verticality_workers
```

---

## ⚙️ Variabel Konfigurasi (Environment Variables)

| Variable | Default | Deskripsi |
|---|---|---|
| `BROKER_HOST` | `emqx.nayakanms.com` | Host broker MQTT |
| `BROKER_PORT` | `1884` | Port broker MQTT |
| `MQTT_USER` | `nyk_ws` | Username MQTT |
| `MQTT_PASS` | `ws` | Password MQTT |
| `INTERVAL_SEC` | `5` | Interval pengiriman data sensor (detik) |
| `HEARTBEAT_SEC` | `60` | Interval pengiriman heartbeat (detik) |
| `CHIP_ID` | *(None)* | Set jika hanya ingin 1 device |
| `MAC_ADDRESS` | *(None)* | MAC address untuk single device |
| `TARGET_CHIPS` | *(None)* | Filter nama chip dipisah koma |

---

## 📋 Daftar 11 Device Terdaftar di `devices.json`

1. `E32_VER_SWADAYA` (`3A:0E:4C:1E:80:6E`)
2. `E32_VER_PEDURENAN` (`D9:DA:D9:08:94:FF`)
3. `E32_VER_SMU84` (`71:0D:4E:CA:62:6A`)
4. `E32_VER_JLNMUSTIKA` (`12:B7:3C:F5:82:0C`)
5. `E32_VER_CIKONDANG` (`10:B7:C8:81:F0:18`)
6. `ESP32_VER_PRMANEN` (`C0:A4:DA:C9:7F:E2`)
7. `E32_VER_BEKASIKOTA` (`E0:8C:FE:34:84:D4`)
8. `E32_VER_GANGAM` (`28:05:A5:24:D5:10`)
9. `E32_VER_SIITU` (`68:09:47:74:B6:54`)
10. `E32_VER_BANTARSARI` (`58:2A:BD:80:F6:34`)
11. `E32_VER_JLABDULSALEH` (`20:50:0D:29:B6:70`)
