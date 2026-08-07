from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Max, Subquery, OuterRef
from django.utils import timezone
from .models import SensorData, SiteVisibility, Site, SensorReading, BLEScan
from .serializers import SensorDataSerializer, SiteVisibilitySerializer, SiteSerializer, SensorReadingSerializer


class SensorDataListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/sensor-data/     → List semua sensor data (terbaru di atas, paginated)
    POST /api/sensor-data/     → Tambah data sensor baru

    Query params:
        ?device_id=CKG-04-031-MM  → Filter by device
    """
    serializer_class = SensorDataSerializer

    def get_queryset(self):
        queryset = SensorData.objects.all()
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset


@api_view(['GET'])
def sensor_data_latest(request):
    """
    GET /api/sensor-data/latest/ → Ambil data sensor terbaru
    GET /api/sensor-data/latest/?device_id=CKG-04-031-MM → Terbaru untuk device tertentu
    """
    queryset = SensorData.objects.all()

    device_id = request.query_params.get('device_id')
    if device_id:
        queryset = queryset.filter(device_id=device_id)

    latest = queryset.first()  # Ordering sudah -timestamp dari model Meta
    if latest is None:
        return Response(
            {'detail': 'Belum ada data sensor.'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = SensorDataSerializer(latest)
    return Response(serializer.data)


@api_view(['GET'])
def sensor_data_history(request):
    """
    GET /api/sensor-data/history/?limit=100 → Ambil N data terakhir (default: 100)
    GET /api/sensor-data/history/?device_id=CKG-04-031-MM → Filter by device
    GET /api/sensor-data/history/?start_date=2026-03-01&end_date=2026-03-04 → Filter by date range
    """
    from django.utils.dateparse import parse_date
    from datetime import datetime, time

    data = SensorData.objects.all()

    # Filter by device_id
    device_id = request.query_params.get('device_id')
    if device_id:
        data = data.filter(device_id=device_id)

    # Filter by date range
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')

    if start_date_str:
        start_date = parse_date(start_date_str)
        if start_date:
            start_datetime = datetime.combine(start_date, time.min)
            data = data.filter(timestamp__gte=start_datetime)

    if end_date_str:
        end_date = parse_date(end_date_str)
        if end_date:
            end_datetime = datetime.combine(end_date, time.max)
            data = data.filter(timestamp__lte=end_datetime)

    limit = int(request.query_params.get('limit', 100))
    limit = min(limit, 5000)  # Max 5000 data for report exports
    data = data[:limit]
    serializer = SensorDataSerializer(data, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def sensor_data_sites_status(request):
    """
    GET /api/sensor-data/sites-status/ → Get latest reading per device_id with live status.
    Returns one entry per device with status: online (< 2min), warning (< 5min), offline (> 5min).
    """
    from datetime import timedelta

    now = timezone.now()
    threshold_online = now - timedelta(minutes=2)
    threshold_warning = now - timedelta(minutes=5)

    # Get latest timestamp per device_id
    latest_ids = (
        SensorData.objects
        .values('device_id')
        .annotate(latest_id=Max('id'))
        .values_list('latest_id', flat=True)
    )

    latest_records = SensorData.objects.filter(id__in=latest_ids).order_by('device_id')

    results = []
    for record in latest_records:
        if record.timestamp >= threshold_online:
            live_status = 'online'
        elif record.timestamp >= threshold_warning:
            live_status = 'warning'
        else:
            live_status = 'offline'

        data = SensorDataSerializer(record).data
        data['live_status'] = live_status
        results.append(data)

    return Response(results)


from rest_framework.views import APIView

class SiteVisibilityView(APIView):
    """
    GET /api/sensor-data/sites-visibility/ -> Ambil daftar visibility semua site.
    POST /api/sensor-data/sites-visibility/ -> Update (upsert) visibilitas site.
    """
    def get(self, request):
        queryset = SiteVisibility.objects.all()
        serializer = SiteVisibilitySerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of boolean mappings"}, status=status.HTTP_400_BAD_REQUEST)
        
        updated = []
        for item in data:
            device_id = item.get('device_id')
            is_hidden = item.get('is_hidden', False)
            if device_id:
                obj, created = SiteVisibility.objects.update_or_create(
                    device_id=device_id,
                    defaults={'is_hidden': is_hidden}
                )
                updated.append(obj)
                
        serializer = SiteVisibilitySerializer(updated, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SiteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/sensor-data/sites/     → List semua site (dengan auto-seeding jika kosong)
    POST /api/sensor-data/sites/     → Tambah site baru
    """
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    pagination_class = None

    def get_queryset(self):
        # Auto-seeding jika tabel Site kosong
        if Site.objects.count() == 0:
            self.seed_default_sites()
        return Site.objects.all()

    def seed_default_sites(self):
        default_sites = [
            {
                'id': 'ckg-04-031',
                'name': 'Nayaka WS',
                'siteId': '20TS10B1529',
                'code': 'E32_VER_WS',
                'lat': -6.237318,
                'lng': 106.919108,
                'area': 'AREA 2',
                'region': 'Jabodetabek Provinsi DKI Jakarta',
                'kabupaten': 'Kota Adm. Jakarta Timur',
                'status': 'online',
                'towerType': 'SST',
                'towerHeight': 42,
            }
        ]
        for s in default_sites:
            Site.objects.get_or_create(id=s['id'], defaults=s)


class SiteRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/sensor-data/sites/<pk>/ → Get detail site
    PUT    /api/sensor-data/sites/<pk>/ → Update site
    DELETE /api/sensor-data/sites/<pk>/ → Hapus site
    """
    queryset = Site.objects.all()
    serializer_class = SiteSerializer


class LatestReadingView(APIView):
    """
    Returns the latest sensor reading. If none exists, creates a baseline initial record.
    """
    def get(self, request):
        latest = SensorReading.objects.first()
        if not latest:
            latest = SensorReading.objects.create(
                node_id='E32_WS (Sector A)',
                temperature=32.04,
                humidity=45.66,
                pressure=100.67,
                wind_speed=0.89,
                wind_direction=324.0,
                rain=27.40,
                light=5817.0,
                radiation=45.0,
                pm25=1.0,
                pm10=2.0,
                negative_ion=138.0,
                noise=0.0
            )
        serializer = SensorReadingSerializer(latest)
        return Response(serializer.data)


class SensorHistoryView(APIView):
    """
    Returns historical readings for charts and data tables. Supports ?range=day|week|month query param.
    Also supports custom date range using ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD.
    """
    def get(self, request):
        import random
        from datetime import datetime, time, timedelta
        from django.utils.dateparse import parse_date

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        range_type = request.query_params.get('range', 'day')
        now = timezone.now()

        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date and end_date:
                start_datetime = datetime.combine(start_date, time.min)
                end_datetime = datetime.combine(end_date, time.max)
                if timezone.is_aware(now):
                    start_datetime = timezone.make_aware(start_datetime)
                    end_datetime = timezone.make_aware(end_datetime)
                
                queryset = SensorReading.objects.filter(
                    timestamp__gte=start_datetime,
                    timestamp__lte=end_datetime
                ).order_by('timestamp')
                has_readings = queryset.exists()
                readings = list(queryset) if has_readings else []
                range_type = 'custom'
                days_diff = (end_date - start_date).days + 1
                limit = max(1, min(days_diff * 4, 100)) # 4 points per day for mock data, max 100
            else:
                has_readings = False
                readings = []
                range_type = 'custom'
                limit = 0
        else:
            if range_type == 'week':
                start_date = now - timedelta(days=7)
                limit = 7
            elif range_type == 'month':
                start_date = now - timedelta(days=30)
                limit = 30
            else: # day
                start_date = now - timedelta(hours=24)
                limit = 24

            queryset = SensorReading.objects.filter(timestamp__gte=start_date).order_by('-timestamp')[:limit]
            has_readings = queryset.exists()
            readings = list(queryset)[::-1] if has_readings else []

        if not has_readings and limit > 0:
            readings = []
            base_temp = 32.04
            base_hum = 45.66
            base_press = 100.67
            base_wind = 0.89

            for i in range(limit):
                if range_type == 'custom' and start_date_str and end_date_str:
                    # Distribute mock dates evenly
                    time_point = start_datetime + timedelta(days=(i * (days_diff) / limit))
                else:
                    time_point = now - timedelta(hours=(limit - i))

                wave = random.uniform(-0.4, 0.4)
                rec = SensorReading(
                    node_id='E32_WS (Sector A)',
                    temperature=round(base_temp + wave * 0.4, 2),
                    humidity=round(base_hum + wave * 0.5, 2),
                    pressure=round(base_press + wave * 0.05, 2),
                    wind_speed=round(max(0.1, base_wind + wave * 0.1), 2),
                    wind_direction=324.0,
                    rain=27.40,
                    light=5817.0,
                    radiation=45.0,
                    pm25=1.0,
                    pm10=2.0,
                    negative_ion=138.0,
                    noise=0.0,
                    timestamp=time_point
                )
                readings.append(rec)

        serializer = SensorReadingSerializer(readings, many=True)
        return Response({
            'range': range_type,
            'count': len(serializer.data),
            'results': serializer.data
        })


class IngestSensorReadingView(APIView):
    """
    POST endpoint for IoT devices / simulation scripts to ingest new sensor readings.
    """
    def post(self, request):
        serializer = SensorReadingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def ble_latest_scans(request):
    """
    Returns the latest scan for the single target BLE antenna (MAC: 7C:D9:F4:03:32:47).
    If no scans exist, returns default missing record.
    """
    mac_target = "7C:D9:F4:03:32:47"
    name_target = "BTSID TII"
    
    latest_scan = BLEScan.objects.filter(mac=mac_target).first()
    
    if latest_scan:
        from datetime import timezone as dt_timezone
        from zoneinfo import ZoneInfo
        jakarta_tz = ZoneInfo('Asia/Jakarta')
        
        scan_time = latest_scan.timestamp
        # Force conversion to UTC to prevent any timezone mismatch/offset bugs
        if timezone.is_aware(scan_time):
            scan_time = scan_time.astimezone(dt_timezone.utc)
        else:
            scan_time = timezone.make_aware(scan_time, dt_timezone.utc)
            
        time_diff = timezone.now() - scan_time
        # Active if scanned within the last 15 seconds
        is_active = time_diff.total_seconds() < 10
        
        status_val = 'Detected' if is_active else 'Missing'
        rssi = latest_scan.rssi
        # Display timestamp in Jakarta timezone (UTC+7)
        timestamp_str = latest_scan.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S')
        uuid = latest_scan.uuid or "AAFE"
        namespace_id = latest_scan.namespace_id or "E157A01861C755AA8C02"
        instance_id = latest_scan.instance_id or "4BC30C720055"
        power = latest_scan.power or "226"
        
        # Theft detection: normal RSSI at ~20m is around -40 to -65 dBm
        # If RSSI drops below -75 dBm, antenna may have been moved/stolen
        if is_active and rssi <= -75:
            theft_alert = 'Suspicious'
        elif not is_active:
            theft_alert = 'No Signal'
        else:
            theft_alert = 'Normal'
    else:
        status_val = 'Missing'
        rssi = -1
        timestamp_str = None
        uuid = "AAFE"
        namespace_id = "E157A01861C755AA8C02"
        instance_id = "4BC30C720055"
        power = "226"
        theft_alert = 'No Signal'
        
    return Response([{
        'mac': mac_target,
        'name': name_target,
        'rssi': rssi,
        'timestamp': timestamp_str,
        'status': status_val,
        'uuid': uuid,
        'namespace_id': namespace_id,
        'instance_id': instance_id,
        'power': power,
        'theft_alert': theft_alert,
    }])


@api_view(['GET'])
def ble_history_chart(request):
    """
    Returns the real-time detection trend (0 or 1) of the target BLE antenna for the last 15 intervals (10 seconds each).
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    mac_target = "7C:D9:F4:03:32:47"
    now = timezone.now()
    results = []
    
    for i in range(14, -1, -1):
        time_point = now - datetime.timedelta(seconds=i * 10)
        start_time = time_point - datetime.timedelta(seconds=10)
        
        scanned = BLEScan.objects.filter(
            mac=mac_target,
            timestamp__gte=start_time,
            timestamp__lte=time_point
        ).exists()
        
        count = 1 if scanned else 0
        # Display time labels in Jakarta timezone (UTC+7)
        time_label = time_point.astimezone(jakarta_tz).strftime('%H:%M:%S')
        
        results.append({
            'date': time_label,
            'count': count
        })
        
    return Response(results)


@api_view(['GET'])
def ble_alerts(request):
    """
    Returns recent BLE theft alert events for the notification panel.
    Checks the last 10 minutes of scans and generates alerts for:
    - Suspicious: RSSI >= -75 (user-defined threshold, means signal too strong = anomaly per user's config)
    - No Signal: No scans received in last 15 seconds
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    mac_target = "7C:D9:F4:03:32:47"
    name_target = "BTSID TII"
    now = timezone.now()
    alerts = []
    
    # Check current status
    latest_scan = BLEScan.objects.filter(mac=mac_target).order_by('-timestamp').first()
    
    if latest_scan:
        from datetime import timezone as dt_timezone
        scan_time = latest_scan.timestamp
        if timezone.is_aware(scan_time):
            scan_time = scan_time.astimezone(dt_timezone.utc)
        else:
            scan_time = timezone.make_aware(scan_time, dt_timezone.utc)
        
        time_diff = (now - scan_time).total_seconds()
        is_active = time_diff < 10
        rssi = latest_scan.rssi
        
        # Current No Signal alert
        if not is_active:
            alerts.append({
                'id': f'ble_nosignal_{int(now.timestamp())}',
                'type': 'ble',
                'title': '⚠️ Antena Tidak Terdeteksi',
                'subtitle': f'{name_target} ({mac_target}) &middot; BLE Scanner',
                'timestamp': now.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                'raw_time': now.isoformat(),
                'severity': 'warning'
            })
        # Current Suspicious RSSI alert  
        elif is_active and rssi <= -75:
            alerts.append({
                'id': f'ble_suspicious_{int(now.timestamp())}',
                'type': 'ble',
                'title': '🚨 Alert: Antena Dicurigai Dicuri!',
                'subtitle': f'{name_target} ({mac_target}) &middot; RSSI: {rssi} dBm',
                'timestamp': latest_scan.timestamp.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                'raw_time': latest_scan.timestamp.isoformat(),
                'severity': 'critical'
            })
    else:
        # No data at all
        alerts.append({
            'id': f'ble_nosignal_{int(now.timestamp())}',
            'type': 'ble',
            'title': '⚠️ Antena Tidak Terdeteksi',
            'subtitle': f'{name_target} ({mac_target}) &middot; BLE Scanner',
            'timestamp': now.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
            'raw_time': now.isoformat(),
            'severity': 'warning'
        })
    
    # Also check recent suspicious scans in the last 10 minutes
    ten_min_ago = now - datetime.timedelta(minutes=10)
    suspicious_scans = BLEScan.objects.filter(
        mac=mac_target,
        rssi__lte=-75,
        timestamp__gte=ten_min_ago
    ).order_by('-timestamp')[:20]
    
    seen_minutes = set()
    for scan in suspicious_scans:
        # Group by minute to avoid flooding notifications
        minute_key = scan.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M')
        if minute_key in seen_minutes:
            continue
        seen_minutes.add(minute_key)
        
        alert_id = f'ble_suspicious_{int(scan.timestamp.timestamp())}'
        # Avoid duplicating the current alert
        if any(a['id'] == alert_id for a in alerts):
            continue
            
        alerts.append({
            'id': alert_id,
            'type': 'ble',
            'title': '🚨 Alert: RSSI Anomali Terdeteksi',
            'subtitle': f'{name_target} ({mac_target}) &middot; RSSI: {scan.rssi} dBm',
            'timestamp': scan.timestamp.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
            'raw_time': scan.timestamp.isoformat(),
            'severity': 'critical'
        })
    
    return Response(alerts)


@api_view(['GET'])
def ble_history_logs(request):
    """
    Returns historical BLE scan logs for a given date range.
    Expected query parameters:
    - start_date: 'YYYY-MM-DD'
    - end_date: 'YYYY-MM-DD'
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    mac_target = "7C:D9:F4:03:32:47"
    name_target = "BTSID TII"
    
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    
    try:
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().astimezone(jakarta_tz).date()
            
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().astimezone(jakarta_tz).date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)

    # Convert local dates to timezone aware datetime objects in Jakarta timezone
    start_datetime = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=jakarta_tz)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=jakarta_tz)
    
    scans = BLEScan.objects.filter(
        mac=mac_target,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    ).order_by('-timestamp')
    
    results = []
    for s in scans:
        theft_alert = 'Suspicious' if s.rssi <= -75 else 'Normal'
        timestamp_str = s.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        results.append({
            'timestamp': timestamp_str,
            'rssi': s.rssi,
            'status': 'Detected',
            'theft_alert': theft_alert,
            'uuid': s.uuid or "AAFE",
            'namespace_id': s.namespace_id or "E157A01861C755AA8C02",
            'instance_id': s.instance_id or "4BC30C720055"
        })
        
    return Response(results)
