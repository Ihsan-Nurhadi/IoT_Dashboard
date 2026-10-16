# Panduan Setup Monitoring Mitratel di VPS & Google Spreadsheet

Dokumen ini berisi panduan lengkap untuk memasang webhook Google Spreadsheet dan memperbarui container service `mitratel_monitor` di VPS Anda.

---

## BAGIAN 1: Setup Google Spreadsheet (Hanya 2 Menit)

1. Buka [Google Sheets](https://sheets.new) baru atau Spreadsheet monitoring yang sudah ada.
2. Beri nama Spreadsheet, misalnya: `Monitoring NMS Mitratel Hourly Matrix`.
3. Pada menu bar atas, klik **Extensions** (Ekstensi) &rarr; **Apps Script**.
4. Hapus seluruh kode bawaan yang ada di editor Apps Script (`myFunction`).
5. Buka file [google_apps_script.js](file:///C:/Users/nasch/Downloads/Dashboard_Ultimate_Nayaka/Worker_Verticality/google_apps_script.js), copy seluruh isinya, lalu paste ke editor Apps Script.
6. Tekan tombol **Save** (ikon disket atau `Ctrl + S`).
7. Di pojok kanan atas, klik tombol biru **Deploy** &rarr; **New deployment**.
8. Klik ikon roda gigi (Select type) di kiri atas pop-up, pilih **Web app**.
9. Konfigurasi:
   * **Description**: `NMS Mitratel Hourly Monitor Webhook`
   * **Execute as**: `Me (<email-anda>)`
   * **Who has access**: `Anyone` *(Wajib "Anyone" agar server VPS dapat mengirimkan data tanpa login)*
10. Klik tombol **Deploy**.
11. Jika muncul jendela otorisasi:
    * Klik *Authorize access*
    * Pilih akun Google Anda
    * Klik *Advanced* &rarr; Klik *Go to Untitled project (unsafe)*
    * Klik *Allow*
12. Salin **Web app URL** yang muncul (formatnya: `https://script.google.com/macros/s/AKfycb.../exec`).

---

## BAGIAN 2: Deployment & Menjalankan di VPS

Metode polling API lama (MaiView HTTP API) sudah sepenuhnya digantikan dengan **Direct MQTT Listener** dan **Google Spreadsheet Sync**.

### 1. Update File Environment di VPS
Tambahkan atau sesuaikan baris berikut di file `.env` direktori project VPS Anda:

```bash
# Konfigurasi MQTT Listener Mitratel
MQTT_BROKER=emqx.nayakanms.com
MQTT_PORT=1884
MQTT_USER=dmtver_jabo
MQTT_PASSWORD=jabo123

# Window mendengarkan MQTT: 300 detik (5 menit) tiap jam
LISTEN_WINDOW_SECONDS=300

# URL Webhook Google Apps Script yang didapat dari Bagian 1
GSHEET_WEBHOOK_URL="https://script.google.com/macros/s/AKfycb.../exec"
```

### 2. Build & Restart Container di VPS
Jalankan perintah berikut pada terminal VPS di root folder project:

```bash
# 1. Rebuild image service mitratel_monitor
docker compose build mitratel_monitor

# 2. Jalankan ulang container di background
docker compose up -d mitratel_monitor
```

### 3. Memantau Log di VPS
Untuk memastikan container berjalan dan siap menunggu pergantian jam:

```bash
docker compose logs -f mitratel_monitor
```

**Output yang diharapkan di log:**
```text
======================================================================
  NMS MITRATEL DEFAULT MONITORING SERVICE (MQTT & GOOGLE SHEETS)
======================================================================
  [OK] Broker       : emqx.nayakanms.com:1884
  [OK] Username     : dmtver_jabo
  [OK] Window Durasi: 300 detik (5 menit)
  [OK] Output Excel : /app/reports/monitoring_mitratel_hourly.xlsx
  [OK] GSheet URL   : https://script.google.com/macros/s/...
  [OK] Mode Loop    : AKTIF (24/7)
======================================================================

[17:00:00] Menunggu hingga awal jam berikutnya: 18:00:00 WIB (Tidur 3598s / 59.9 menit)...
```

---

## BAGIAN 3: Cara Kerja Otomatis di VPS

1. **Menit 00:00 WIB (Awal Jam)**:
   * Worker bangun dan langsung membuka koneksi ke broker MQTT `emqx.nayakanms.com:1884`.
   * Melakukan subscribe ke topik telemetri seluruh site (`nms/+/vertical/#`).
2. **Menit 00:00 - 05:00 WIB (Window 5 Menit)**:
   * Mengumpulkan semua data/paket masuk dari 61 site.
3. **Menit 05:00 WIB**:
   * Menutup koneksi MQTT.
   * Mengevaluasi site: site yang mengirim data berstatus **ONLINE**, yang tidak mengirim data berstatus **OFFLINE**.
   * Mengirim hasil evaluasi ke **Google Spreadsheet** (membuat sheet tanggal baru jika hari berganti dan mewarnai hijau/merah pada kolom jam terkait).
   * Memperbarui matriks di file Excel lokal (`/app/reports/monitoring_mitratel_hourly.xlsx`) agar fitur unduh di dashboard web tetap bekerja.
4. **Menit 05:01 - 59:59 WIB**:
   * Worker *sleep* (idle) menghemat beban CPU & bandwidth VPS selama 55 menit hingga jam berikutnya tiba.
