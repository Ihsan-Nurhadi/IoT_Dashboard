from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Max, Subquery, OuterRef, Count
from django.utils import timezone
from .models import SensorData, SiteVisibility, Site, SensorReading, BLEScan, RFIDScan, RegisteredRFIDTag, RegisteredRFIDReader
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
    Returns the latest scans for all active registered BLE devices.
    If no devices are registered, returns an empty list.
    """
    from datetime import timezone as dt_timezone
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    devices = BLEDevice.objects.filter(is_active=True)
    if not devices.exists():
        return Response([])

    results = []
    for device in devices:
        latest_scan = BLEScan.objects.filter(mac=device.mac).first()
        image_url = device.image.url if device.image else None
        
        if latest_scan:
            scan_time = latest_scan.timestamp
            if timezone.is_aware(scan_time):
                scan_time = scan_time.astimezone(dt_timezone.utc)
            else:
                scan_time = timezone.make_aware(scan_time, dt_timezone.utc)
                
            time_diff = timezone.now() - scan_time
            is_active = time_diff.total_seconds() < 10
            
            status_val = 'Detected' if is_active else 'Missing'
            rssi = latest_scan.rssi
            timestamp_str = latest_scan.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S')
            uuid = latest_scan.uuid or "AAFE"
            namespace_id = latest_scan.namespace_id or "E157A01861C755AA8C02"
            instance_id = latest_scan.instance_id or "4BC30C720055"
            power = latest_scan.power or "226"
            
            threshold = device.rssi_threshold
            if is_active and rssi <= threshold:
                theft_alert = 'Suspicious'
            elif not is_active:
                theft_alert = 'No Signal'
            else:
                theft_alert = 'Normal'
        else:
            status_val = 'Missing'
            rssi = -100
            timestamp_str = None
            uuid = "AAFE"
            namespace_id = "E157A01861C755AA8C02"
            instance_id = "4BC30C720055"
            power = "226"
            theft_alert = 'No Signal'
            
        results.append({
            'mac': device.mac,
            'name': device.name,
            'location': device.location,
            'installation_date': device.installation_date.strftime('%d %B %Y') if device.installation_date else 'Never',
            'vendor': device.vendor,
            'height': device.height,
            'image': image_url,
            'rssi': rssi,
            'timestamp': timestamp_str,
            'status': status_val,
            'uuid': uuid,
            'namespace_id': namespace_id,
            'instance_id': instance_id,
            'power': power,
            'theft_alert': theft_alert,
        })
        
    return Response(results)


@api_view(['GET'])
def ble_history_chart(request):
    """
    Returns the real-time detection trend (total count of active registered antennas) 
    for the last 15 intervals (10 seconds each).
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    active_devices = BLEDevice.objects.filter(is_active=True)
    now = timezone.now()
    results = []
    
    for i in range(14, -1, -1):
        time_point = now - datetime.timedelta(seconds=i * 10)
        start_time = time_point - datetime.timedelta(seconds=10)
        
        active_count = 0
        for device in active_devices:
            scanned = BLEScan.objects.filter(
                mac=device.mac,
                timestamp__gte=start_time,
                timestamp__lte=time_point
            ).exists()
            if scanned:
                active_count += 1
                
        time_label = time_point.astimezone(jakarta_tz).strftime('%H:%M:%S')
        
        results.append({
            'date': time_label,
            'count': active_count
        })
        
    return Response(results)


@api_view(['GET'])
def ble_alerts(request):
    """
    Returns recent BLE theft alert events for the notification panel for all registered BLE devices.
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    from datetime import timezone as dt_timezone
    
    devices = BLEDevice.objects.filter(is_active=True)
    now = timezone.now()
    alerts = []
    
    for device in devices:
        mac_target = device.mac
        name_target = device.name
        threshold = device.rssi_threshold
        
        latest_scan = BLEScan.objects.filter(mac=mac_target).order_by('-timestamp').first()
        
        if latest_scan:
            scan_time = latest_scan.timestamp
            if timezone.is_aware(scan_time):
                scan_time = scan_time.astimezone(dt_timezone.utc)
            else:
                scan_time = timezone.make_aware(scan_time, dt_timezone.utc)
            
            time_diff = (now - scan_time).total_seconds()
            is_active = time_diff < 10
            rssi = latest_scan.rssi
            
            if not is_active:
                alerts.append({
                    'id': f'ble_nosignal_{mac_target.replace(":", "")}_{int(now.timestamp())}',
                    'type': 'ble',
                    'title': f'⚠️ Antena {name_target} Tidak Terdeteksi',
                    'subtitle': f'{name_target} ({mac_target}) &middot; BLE Scanner',
                    'timestamp': now.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                    'raw_time': now.isoformat(),
                    'severity': 'warning'
                })
            elif is_active and rssi <= threshold:
                alerts.append({
                    'id': f'ble_suspicious_{mac_target.replace(":", "")}_{int(now.timestamp())}',
                    'type': 'ble',
                    'title': f'🚨 Alert: Antena {name_target} Dicurigai Dicuri!',
                    'subtitle': f'{name_target} ({mac_target}) &middot; RSSI: {rssi} dBm (Threshold: {threshold} dBm)',
                    'timestamp': latest_scan.timestamp.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                    'raw_time': latest_scan.timestamp.isoformat(),
                    'severity': 'critical'
                })
        else:
            alerts.append({
                'id': f'ble_nosignal_{mac_target.replace(":", "")}_{int(now.timestamp())}',
                'type': 'ble',
                'title': f'⚠️ Antena {name_target} Tidak Terdeteksi',
                'subtitle': f'{name_target} ({mac_target}) &middot; BLE Scanner',
                'timestamp': now.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                'raw_time': now.isoformat(),
                'severity': 'warning'
            })
        
        ten_min_ago = now - datetime.timedelta(minutes=10)
        suspicious_scans = BLEScan.objects.filter(
            mac=mac_target,
            rssi__lte=threshold,
            timestamp__gte=ten_min_ago
        ).order_by('-timestamp')[:10]
        
        seen_minutes = set()
        for scan in suspicious_scans:
            minute_key = scan.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M')
            if minute_key in seen_minutes:
                continue
            seen_minutes.add(minute_key)
            
            alert_id = f'ble_suspicious_{mac_target.replace(":", "")}_{int(scan.timestamp.timestamp())}'
            if any(a['id'] == alert_id for a in alerts):
                continue
                
            alerts.append({
                'id': alert_id,
                'type': 'ble',
                'title': f'🚨 Alert: RSSI Anomali {name_target} Terdeteksi',
                'subtitle': f'{name_target} ({mac_target}) &middot; RSSI: {scan.rssi} dBm (Threshold: {threshold} dBm)',
                'timestamp': scan.timestamp.astimezone(jakarta_tz).strftime('%b %d, %I:%M %p'),
                'raw_time': scan.timestamp.isoformat(),
                'severity': 'critical'
            })
            
    severity_order = {'critical': 0, 'warning': 1}
    alerts.sort(key=lambda x: (severity_order.get(x['severity'], 2), x['raw_time']), reverse=True)
    return Response(alerts)


@api_view(['GET'])
def ble_history_logs(request):
    """
    Returns historical BLE scan logs for a given date range and optional MAC address.
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    mac_target = request.query_params.get('mac')
    if not mac_target:
        first_device = BLEDevice.objects.filter(is_active=True).first()
        if first_device:
            mac_target = first_device.mac
        else:
            mac_target = "7C:D9:F4:03:32:47"
            
    device = BLEDevice.objects.filter(mac=mac_target).first()
    threshold = device.rssi_threshold if device else -75
    
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

    start_datetime = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=jakarta_tz)
    end_datetime = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=jakarta_tz)
    
    scans = BLEScan.objects.filter(
        mac=mac_target,
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    ).order_by('-timestamp')
    
    results = []
    for s in scans:
        theft_alert = 'Suspicious' if s.rssi <= threshold else 'Normal'
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


# ==========================================
# AUTHENTICATION & BLE DEVICE CRUD APIS
# ==========================================
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import get_object_or_404
from .models import BLEDevice

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def api_login(request):
    """
    Authenticates user and logs them in using Django's session system.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        auth_login(request, user)
        return Response({
            'success': True,
            'username': user.username
        })
    else:
        return Response({
            'success': False,
            'message': 'Username atau password salah.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def api_logout(request):
    """
    Logs out the user.
    """
    auth_logout(request)
    return Response({'success': True})


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def api_auth_status(request):
    """
    Checks if session is authenticated.
    """
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'username': request.user.username
        })
    return Response({
        'authenticated': False
    })


@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def ble_devices_list(request):
    """
    List all configured BLE devices (public) or register a new BLE device (admin only).
    """
    if request.method == 'GET':
        devices = BLEDevice.objects.all()
        data = []
        for d in devices:
            image_url = d.image.url if d.image else None
            data.append({
                'mac': d.mac,
                'name': d.name,
                'location': d.location,
                'installation_date': d.installation_date,
                'vendor': d.vendor,
                'height': d.height,
                'rssi_threshold': d.rssi_threshold,
                'image': image_url,
                'is_active': d.is_active,
            })
        return Response(data)

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        mac = request.data.get('mac')
        if mac:
            mac = mac.strip().upper()
            
        name = request.data.get('name')
        location = request.data.get('location', 'Sector A - Upper Level')
        installation_date_str = request.data.get('installation_date')
        vendor = request.data.get('vendor', 'Huawei')
        height = request.data.get('height', '38 Meter')
        rssi_threshold_val = request.data.get('rssi_threshold', -75)
        
        try:
            rssi_threshold = int(rssi_threshold_val) if rssi_threshold_val not in (None, '', 'null') else -75
        except (ValueError, TypeError):
            rssi_threshold = -75
            
        is_active_str = request.data.get('is_active', 'true')
        is_active = is_active_str.lower() == 'true' if isinstance(is_active_str, str) else bool(is_active_str)
        image = request.FILES.get('image')

        if not mac or not name:
            return Response({'error': 'MAC and Name are required'}, status=status.HTTP_400_BAD_REQUEST)

        installation_date = None
        if installation_date_str and installation_date_str != 'null' and installation_date_str != '':
            try:
                from django.utils.dateparse import parse_date
                installation_date = parse_date(installation_date_str)
            except Exception:
                pass

        try:
            device = BLEDevice.objects.create(
                mac=mac,
                name=name,
                location=location,
                installation_date=installation_date,
                vendor=vendor,
                height=height,
                rssi_threshold=rssi_threshold,
                is_active=is_active,
                image=image
            )
            image_url = device.image.url if device.image else None
            return Response({
                'mac': device.mac,
                'name': device.name,
                'location': device.location,
                'installation_date': device.installation_date,
                'vendor': device.vendor,
                'height': device.height,
                'rssi_threshold': device.rssi_threshold,
                'image': image_url,
                'is_active': device.is_active,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def ble_device_detail(request, mac):
    """
    Get (public), Update (admin only), or Delete (admin only) a specific BLE device configuration.
    """
    device = get_object_or_404(BLEDevice, mac=mac)

    if request.method == 'GET':
        image_url = device.image.url if device.image else None
        return Response({
            'mac': device.mac,
            'name': device.name,
            'location': device.location,
            'installation_date': device.installation_date,
            'vendor': device.vendor,
            'height': device.height,
            'rssi_threshold': device.rssi_threshold,
            'image': image_url,
            'is_active': device.is_active,
        })

    if not request.user.is_authenticated:
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'PUT':
        name = request.data.get('name')
        location = request.data.get('location')
        installation_date_str = request.data.get('installation_date')
        vendor = request.data.get('vendor')
        height = request.data.get('height')
        rssi_threshold = request.data.get('rssi_threshold')
        is_active_str = request.data.get('is_active')
        
        if name:
            device.name = name
        if location:
            device.location = location
        
        if installation_date_str is not None:
            if installation_date_str in ('', 'null', 'None'):
                device.installation_date = None
            else:
                try:
                    from django.utils.dateparse import parse_date
                    device.installation_date = parse_date(installation_date_str)
                except Exception:
                    pass
        if vendor:
            device.vendor = vendor
        if height:
            device.height = height
        if rssi_threshold is not None:
            try:
                device.rssi_threshold = int(rssi_threshold)
            except ValueError:
                pass
        if is_active_str is not None:
            device.is_active = is_active_str.lower() == 'true' if isinstance(is_active_str, str) else bool(is_active_str)

        # Handle image file upload or clearing
        if 'image' in request.FILES:
            if device.image:
                try:
                    device.image.delete(save=False)
                except Exception:
                    pass
            device.image = request.FILES['image']
        elif request.data.get('image') == 'null' or request.data.get('clear_image') == 'true':
            if device.image:
                try:
                    device.image.delete(save=False)
                except Exception:
                    pass
            device.image = None

        device.save()
        image_url = device.image.url if device.image else None
        return Response({
            'mac': device.mac,
            'name': device.name,
            'location': device.location,
            'installation_date': device.installation_date,
            'vendor': device.vendor,
            'height': device.height,
            'rssi_threshold': device.rssi_threshold,
            'image': image_url,
            'is_active': device.is_active,
        })

    elif request.method == 'DELETE':
        if device.image:
            try:
                device.image.delete(save=False)
            except Exception:
                pass
        device.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def ble_device_delete_post(request, mac):
    """
    Delete a specific BLE device configuration using POST method (to bypass firewalls/proxies blocking DELETE).
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
    device = get_object_or_404(BLEDevice, mac=mac)
    if device.image:
        try:
            device.image.delete(save=False)
        except Exception:
            pass
    device.delete()
    return Response({'success': True}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def ble_unregistered_list(request):
    """
    Returns unique MAC addresses seen by MQTT recently that are not registered.
    """
    if not request.user.is_authenticated:
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    from django.db.models import Max
    import datetime
    
    time_limit = timezone.now() - datetime.timedelta(hours=24)
    registered_macs = BLEDevice.objects.values_list('mac', flat=True)
    
    recent_scans = BLEScan.objects.filter(
        timestamp__gte=time_limit
    ).exclude(
        mac__in=registered_macs
    ).values('mac').annotate(
        latest_time=Max('timestamp')
    ).order_by('-latest_time')[:50]
    
    results = []
    for item in recent_scans:
        mac = item['mac']
        last_scan = BLEScan.objects.filter(mac=mac, timestamp=item['latest_time']).first()
        if last_scan:
            results.append({
                'mac': mac,
                'name': last_scan.name,
                'rssi': last_scan.rssi,
                'last_seen': last_scan.timestamp
            })
            
    return Response(results)


@api_view(['GET'])
def rfid_latest_scans(request):
    """
    Returns the latest RFID scans of registered tags.
    """
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    registered_tags = list(RegisteredRFIDTag.objects.all().values_list('tag_epc', flat=True))
    scans = RFIDScan.objects.filter(tag_epc__in=registered_tags).order_by('-timestamp')[:20]
    reader_map = {r.reader_id: r.name for r in RegisteredRFIDReader.objects.all() if r.name}
    
    results = []
    for s in scans:
        custom_name = reader_map.get(s.reader_id)
        display_reader = custom_name if custom_name else s.reader_id
        results.append({
            'id': s.id,
            'timestamp': s.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S'),
            'reader_id': display_reader,
            'tag_epc': s.tag_epc
        })
    return Response(results)


@api_view(['GET'])
def rfid_history_logs(request):
    """
    Returns either:
    1. Grouped unique registered RFID tags with latest scan details (default).
    2. Raw individual scan logs of registered tags if raw_scans=true.
    """
    import datetime
    from zoneinfo import ZoneInfo
    jakarta_tz = ZoneInfo('Asia/Jakarta')
    
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    tag_epc = request.query_params.get('tag_epc')
    raw_scans = request.query_params.get('raw_scans') == 'true'
    
    registered_tags = list(RegisteredRFIDTag.objects.all().values_list('tag_epc', flat=True))
    
    start_datetime = None
    end_datetime = None
    try:
        if start_date_str:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            start_datetime = datetime.datetime.combine(start_date, datetime.time.min).replace(tzinfo=jakarta_tz)
        if end_date_str:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            end_datetime = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=jakarta_tz)
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
    reader_map = {r.reader_id: r.name for r in RegisteredRFIDReader.objects.all() if r.name}
    
    if raw_scans:
        scans = RFIDScan.objects.filter(tag_epc__in=registered_tags)
        if start_datetime:
            scans = scans.filter(timestamp__gte=start_datetime)
        if end_datetime:
            scans = scans.filter(timestamp__lte=end_datetime)
        if tag_epc:
            scans = scans.filter(tag_epc__icontains=tag_epc)
            
        scans = scans.order_by('-timestamp')
        results = []
        for s in scans:
            custom_name = reader_map.get(s.reader_id)
            display_reader = custom_name if custom_name else s.reader_id
            results.append({
                'timestamp': s.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S'),
                'reader_id': display_reader,
                'tag_epc': s.tag_epc
            })
        return Response(results)
        
    tags = RegisteredRFIDTag.objects.all()
    if tag_epc:
        tags = tags.filter(tag_epc__icontains=tag_epc)
        
    results = []
    for tag in tags:
        scans = RFIDScan.objects.filter(tag_epc=tag.tag_epc)
        if start_datetime:
            scans = scans.filter(timestamp__gte=start_datetime)
        if end_datetime:
            scans = scans.filter(timestamp__lte=end_datetime)
            
        latest_scan = scans.order_by('-timestamp').first()
        
        if latest_scan:
            last_scan_time = latest_scan.timestamp.astimezone(jakarta_tz).strftime('%Y-%m-%d %H:%M:%S')
            raw_reader = latest_scan.reader_id
            custom_name = reader_map.get(raw_reader)
            display_reader = custom_name if custom_name else raw_reader
        else:
            if start_date_str or end_date_str:
                continue
            last_scan_time = ''
            display_reader = '-'
            
        results.append({
            'tag_epc': tag.tag_epc,
            'last_scan': last_scan_time,
            'last_reader': display_reader,
        })
        
    results.sort(key=lambda x: x['last_scan'] or '0000-00-00 00:00:00', reverse=True)
    return Response(results)


def publish_rfid_config():
    """
    Publishes the whitelisted EPC tags to the MQTT topic rfid/config.
    Using retain=True allows newly connected clients to receive the latest config immediately.
    """
    import paho.mqtt.client as mqtt
    import json
    import time
    try:
        tags = list(RegisteredRFIDTag.objects.filter(is_active=True).values_list('tag_epc', flat=True))
        # Ensure the tags are sanitized (uppercase and trimmed)
        tags = [t.upper().strip() for t in tags]
        payload = json.dumps({'allowed_tags': tags})

        # Use CallbackAPIVersion.VERSION2 if available (paho >= 2.0)
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="django_rfid_publisher_temp"
            )
        except AttributeError:
            client = mqtt.Client(client_id="django_rfid_publisher_temp")

        # Use loop_start so the network loop runs in background while we wait for connection
        client.loop_start()
        client.connect("broker.emqx.io", 1883, 60)
        # Wait briefly for the connection to be established before publishing
        time.sleep(1.5)
        result = client.publish("rfid/config", payload, qos=1, retain=True)
        # Wait for the message to be sent (important for QoS 1)
        result.wait_for_publish(timeout=5)
        client.loop_stop()
        client.disconnect()
        print("Successfully published RFID config to MQTT with retain=True:", payload)
    except Exception as e:
        print("Failed to publish RFID config to MQTT:", e)


@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def rfid_tags_list(request):
    """
    List all configured RFID tags (public) or register a new RFID tag (admin only).
    """
    if request.method == 'GET':
        tags = RegisteredRFIDTag.objects.all()
        data = []
        for t in tags:
            data.append({
                'tag_epc': t.tag_epc,
                'name': t.name,
                'is_active': t.is_active,
                'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S') if t.created_at else None,
            })
        return Response(data)

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        tag_epc = request.data.get('tag_epc')
        if tag_epc:
            tag_epc = tag_epc.strip().upper()
            
        name = request.data.get('name')
        is_active_val = request.data.get('is_active', True)
        is_active = is_active_val.lower() == 'true' if isinstance(is_active_val, str) else bool(is_active_val)

        if not tag_epc:
            return Response({'error': 'EPC Tag is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tag = RegisteredRFIDTag.objects.create(
                tag_epc=tag_epc,
                name=name,
                is_active=is_active
            )
            # Trigger MQTT publish sync
            publish_rfid_config()
            
            return Response({
                'tag_epc': tag.tag_epc,
                'name': tag.name,
                'is_active': tag.is_active,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def rfid_tag_detail(request, tag_epc):
    """
    Get, Update, or Delete a specific registered RFID tag.
    """
    tag_epc = tag_epc.strip().upper()
    tag = get_object_or_404(RegisteredRFIDTag, tag_epc=tag_epc)

    if request.method == 'GET':
        return Response({
            'tag_epc': tag.tag_epc,
            'name': tag.name,
            'is_active': tag.is_active,
        })

    if not request.user.is_authenticated:
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'PUT':
        name = request.data.get('name')
        is_active_val = request.data.get('is_active')
        
        if name is not None:
            tag.name = name
        if is_active_val is not None:
            tag.is_active = is_active_val.lower() == 'true' if isinstance(is_active_val, str) else bool(is_active_val)
            
        tag.save()
        # Trigger MQTT publish sync
        publish_rfid_config()
        
        return Response({
            'tag_epc': tag.tag_epc,
            'name': tag.name,
            'is_active': tag.is_active,
        })

    elif request.method == 'DELETE':
        tag.delete()
        # Trigger MQTT publish sync
        publish_rfid_config()
        return Response({'detail': 'RFID Tag deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def rfid_readers_list(request):
    """
    List all configured RFID readers (public) or register a new RFID reader (admin only).
    """
    if request.method == 'GET':
        readers = RegisteredRFIDReader.objects.all()
        data = []
        for r in readers:
            data.append({
                'reader_id': r.reader_id,
                'name': r.name,
                'is_active': r.is_active,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else None,
            })
        return Response(data)

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        reader_id = request.data.get('reader_id')
        if reader_id:
            reader_id = reader_id.strip()
            
        name = request.data.get('name')
        is_active_val = request.data.get('is_active', True)
        is_active = is_active_val.lower() == 'true' if isinstance(is_active_val, str) else bool(is_active_val)

        if not reader_id:
            return Response({'error': 'Reader ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reader = RegisteredRFIDReader.objects.create(
                reader_id=reader_id,
                name=name,
                is_active=is_active
            )
            # Trigger MQTT publish sync so the new reader config is pushed
            publish_rfid_config()
            return Response({
                'reader_id': reader.reader_id,
                'name': reader.name,
                'is_active': reader.is_active,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([AllowAny])
def rfid_reader_detail(request, reader_id):
    """
    Get, Update, or Delete a specific registered RFID reader.
    """
    reader_id = reader_id.strip()
    reader = get_object_or_404(RegisteredRFIDReader, reader_id=reader_id)

    if request.method == 'GET':
        return Response({
            'reader_id': reader.reader_id,
            'name': reader.name,
            'is_active': reader.is_active,
        })

    if not request.user.is_authenticated:
        return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'PUT':
        name = request.data.get('name')
        is_active_val = request.data.get('is_active')
        
        if name is not None:
            reader.name = name
        if is_active_val is not None:
            reader.is_active = is_active_val.lower() == 'true' if isinstance(is_active_val, str) else bool(is_active_val)
            
        reader.save()
        # Trigger MQTT publish sync
        publish_rfid_config()
        return Response({
            'reader_id': reader.reader_id,
            'name': reader.name,
            'is_active': reader.is_active,
        })

    elif request.method == 'DELETE':
        reader.delete()
        # Trigger MQTT publish sync
        publish_rfid_config()
        return Response({'detail': 'RFID Reader deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


