from django.db import models


class SensorData(models.Model):
    """
    Model untuk menyimpan data sensor dari Structural Health Monitoring.
    Data diterima melalui MQTT dari topic tower/bts/nyk/verticality/data/site/dmt/telemetry.
    Setiap record memiliki device_id untuk membedakan site.
    """
    device_id = models.CharField(
        max_length=50,
        default='DPK',
        db_index=True,
        help_text='ID perangkat/site (contoh: CKG-04-031-MM)'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Waktu data diterima'
    )
    wind_speed = models.FloatField(
        default=0.0,
        help_text='Kecepatan angin dalam knot'
    )
    wind_speed_ms = models.FloatField(
        default=0.0,
        help_text='Kecepatan angin dalam m/s'
    )
    pitch = models.FloatField(
        default=0.0,
        help_text='Sudut pitch dalam derajat'
    )
    roll = models.FloatField(
        default=0.0,
        help_text='Sudut roll dalam derajat'
    )
    tilt_rate = models.FloatField(
        default=0.0,
        help_text='Laju kemiringan dalam derajat'
    )
    sway = models.FloatField(
        default=0.0,
        help_text='Perpindahan sway dalam mm'
    )
    total_tilt = models.FloatField(
        default=0.0,
        help_text='Total kemiringan dalam derajat'
    )
    indikator = models.CharField(
        max_length=20,
        default='tolerance',
        choices=[('tolerance', 'Tolerance'), ('intolerance', 'Intolerance')],
        help_text='Indikator status: tolerance atau intolerance'
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Sensor Data'
        verbose_name_plural = 'Sensor Data'
        indexes = [
            models.Index(fields=['device_id', '-timestamp']),
        ]

    def __str__(self):
        return f"SensorData [{self.device_id}] [{self.timestamp:%Y-%m-%d %H:%M:%S}] - Wind: {self.wind_speed}, Tilt: {self.total_tilt}°"


class SiteVisibility(models.Model):
    """
    Model ini menyimpan konfigurasi visibilitas site di dashboard.
    Data ini akan disinkronisasikan ke semua klien (browser).
    Jika is_hidden = True, site tidak akan ditampilkan di Site Map dan Sidebar.
    """
    device_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='ID perangkat/site (contoh: KDS-06-039-MS)'
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text='Apakah site ini disembunyikan dari dashboard?'
    )

    class Meta:
        verbose_name = 'Site Visibility'
        verbose_name_plural = 'Site Visibilities'

    def __str__(self):
        status = "Hidden" if self.is_hidden else "Visible"
        return f"Visibility [{self.device_id}] - {status}"


class Site(models.Model):
    """
    Model untuk menyimpan konfigurasi dan metadata site secara dinamis.
    """
    id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text='ID unik site (contoh: ckg-04-031)'
    )
    name = models.CharField(
        max_length=100,
        help_text='Nama site'
    )
    siteId = models.CharField(
        max_length=50,
        help_text='Site ID (contoh: 20TS10B1529)'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text='Kode site/device_id (contoh: CKG-04-031-MM)'
    )
    lat = models.FloatField(help_text='Latitude')
    lng = models.FloatField(help_text='Longitude')
    area = models.CharField(
        max_length=50,
        help_text='Area (contoh: AREA 2)'
    )
    region = models.CharField(
        max_length=100,
        help_text='Region'
    )
    kabupaten = models.CharField(
        max_length=100,
        help_text='Kabupaten/Kota'
    )
    status = models.CharField(
        max_length=20,
        default='offline',
        help_text='Status awal'
    )
    towerType = models.CharField(
        max_length=50,
        help_text='Tipe Tower (contoh: SST)'
    )
    towerHeight = models.FloatField(help_text='Tinggi Tower dalam meter')
    isHidden = models.BooleanField(
        default=False,
        help_text='Apakah site disembunyikan secara default?'
    )

    class Meta:
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'

    def __str__(self):
        return f"Site {self.name} ({self.code})"


class SensorReading(models.Model):
    node_id = models.CharField(max_length=50, default='E32_WS (Sector A)')
    temperature = models.FloatField(default=32.04, help_text="Suhu dalam °C")
    humidity = models.FloatField(default=45.66, help_text="Kelembapan dalam %RH")
    pressure = models.FloatField(default=100.67, help_text="Tekanan dalam kPa")
    wind_speed = models.FloatField(default=0.89, help_text="Kecepatan Angin dalam m/s")
    wind_direction = models.FloatField(default=324.0, help_text="Arah Angin dalam derajat")
    rain = models.FloatField(default=27.40, help_text="Curah Hujan dalam mm")
    light = models.FloatField(default=5817.0, help_text="Cahaya dalam lux")
    radiation = models.FloatField(default=45.0, help_text="Radiasi dalam W/m2")
    pm25 = models.FloatField(default=1.0, help_text="PM2.5 dalam ug/m3")
    pm10 = models.FloatField(default=2.0, help_text="PM10 dalam ug/m3")
    negative_ion = models.FloatField(default=138.0, help_text="Ion Negatif dalam ion/cm3")
    noise = models.FloatField(default=0.0, help_text="Kebisingan dalam dB")

    # Legacy optional fields
    co = models.FloatField(null=True, blank=True, default=None)
    co2 = models.FloatField(null=True, blank=True, default=None)
    no2 = models.FloatField(null=True, blank=True, default=None)
    so2 = models.FloatField(null=True, blank=True, default=None)
    aqi = models.IntegerField(null=True, blank=True, default=None)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.node_id} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class BLEDevice(models.Model):
    mac = models.CharField(max_length=50, unique=True, primary_key=True, help_text="MAC Address BLE Beacon")
    name = models.CharField(max_length=100, help_text="Nama unik perangkat (contoh: BTSID TII)")
    location = models.CharField(max_length=100, default="Sector A - Upper Level", help_text="Deskripsi lokasi pemasangan")
    installation_date = models.DateField(null=True, blank=True, help_text="Tanggal pemasangan perangkat")
    vendor = models.CharField(max_length=50, default="Huawei", help_text="Vendor perangkat")
    height = models.CharField(max_length=50, default="38 Meter", help_text="Tinggi pemasangan di tower")
    rssi_threshold = models.IntegerField(default=-75, help_text="Ambang batas RSSI untuk deteksi pencurian (default: -75 dBm)")
    image = models.FileField(upload_to='ble_devices/', null=True, blank=True, help_text="Gambar/Foto Antena")
    is_active = models.BooleanField(default=True, help_text="Status pemantauan aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'BLE Device Config'
        verbose_name_plural = 'BLE Device Configs'

    def __str__(self):
        return f"{self.name} ({self.mac})"


class BLEScan(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    mac = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=100)
    rssi = models.IntegerField()
    uuid = models.CharField(max_length=50, blank=True, null=True)
    namespace_id = models.CharField(max_length=50, blank=True, null=True)
    instance_id = models.CharField(max_length=50, blank=True, null=True)
    power = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'BLE Scan'
        verbose_name_plural = 'BLE Scans'

    def __str__(self):
        return f"{self.name} ({self.mac}) - RSSI: {self.rssi} at {self.timestamp}"


class RFIDScan(models.Model):
    timestamp = models.DateTimeField(db_index=True, help_text="Timestamp of scan log")
    reader_id = models.CharField(max_length=100, db_index=True, help_text="ID of the RFID reader")
    tag_epc = models.CharField(max_length=100, db_index=True, help_text="EPC ID of the RFID tag scanned")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'RFID Scan'
        verbose_name_plural = 'RFID Scans'

    def __str__(self):
        return f"{self.tag_epc} scanned by {self.reader_id} at {self.timestamp}"


class RegisteredRFIDTag(models.Model):
    tag_epc = models.CharField(max_length=100, unique=True, db_index=True, help_text="EPC ID of the registered RFID tag")
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Custom name/label for the tag")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tag_epc']
        verbose_name = 'Registered RFID Tag'
        verbose_name_plural = 'Registered RFID Tags'

    def __str__(self):
        return f"{self.tag_epc} - {self.name or 'Unnamed'}"


class RegisteredRFIDReader(models.Model):
    reader_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="ID of the registered RFID reader")
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Custom name/label for the reader")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['reader_id']
        verbose_name = 'Registered RFID Reader'
        verbose_name_plural = 'Registered RFID Readers'

    def __str__(self):
        return f"{self.reader_id} - {self.name or 'Unnamed'}"


class CableHealthTelemetry(models.Model):
    """
    Model untuk menyimpan data telemetri kesehatan kabel (Cable Sense).
    Dipantau: perubahan mekanis (getaran, tarik, benturan), pencurian (is_cut),
    suhu, dan status perangkat (sinyal, koneksi).
    """
    device_id = models.CharField(
        max_length=50,
        default='Cable_Sense_01',
        db_index=True,
        help_text='ID perangkat sensor kabel'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Waktu data diterima'
    )
    vibration = models.FloatField(
        default=0.0,
        help_text='Getaran kabel (vibration) dalam m/s² atau g'
    )
    tension = models.FloatField(
        default=100.0,
        help_text='Tegangan tarik kabel (tension) dalam % atau kg'
    )
    impact = models.FloatField(
        default=0.0,
        help_text='Benturan mekanis (impact) dalam g'
    )
    is_cut = models.BooleanField(
        default=False,
        help_text='Indikator aktivitas pencurian (kabel dipotong/dilepas)'
    )
    temperature = models.FloatField(
        default=25.0,
        help_text='Suhu kabel/lingkungan dalam °C'
    )
    device_status = models.CharField(
        max_length=20,
        default='Normal',
        choices=[
            ('Normal', 'Normal'),
            ('Warning', 'Warning'),
            ('Critical', 'Critical'),
            ('Offline', 'Offline')
        ],
        help_text='Kondisi kesehatan/status perangkat'
    )
    signal_strength = models.IntegerField(
        default=-60,
        help_text='Kekuatan sinyal RSSI dalam dBm'
    )
    is_connected = models.BooleanField(
        default=True,
        help_text='Status konektivitas perangkat ke gateway'
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Cable Health Telemetry'
        verbose_name_plural = 'Cable Health Telemetry Logs'
        indexes = [
            models.Index(fields=['device_id', '-timestamp']),
        ]

    def __str__(self):
        return f"CableHealth [{self.device_id}] [{self.timestamp:%Y-%m-%d %H:%M:%S}] - Status: {self.device_status}"

