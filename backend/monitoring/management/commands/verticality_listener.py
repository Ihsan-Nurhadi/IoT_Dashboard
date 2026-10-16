import json
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from monitoring.models import SensorData

# In-memory device cache to preserve telemetry between separate tilt & wind MQTT messages
DEVICE_CACHE = {}


def extract_device_id(topic: str, payload: dict) -> str:
    """
    Ekstrak ID device dari topic MQTT (contoh: nms/E32_VER_WEES/vertical/tilt -> E32_VER_WEES)
    atau dari payload JSON jika tersedia.
    """
    if isinstance(payload, dict):
        if payload.get('device_id'):
            return str(payload['device_id'])
        if payload.get('client_id'):
            return str(payload['client_id'])

    parts = topic.split('/')
    if len(parts) >= 2 and parts[0] == 'nms':
        return parts[1]

    return 'E32_VER_WEES'


def update_device_telemetry(device_id: str, topic: str, payload: dict) -> dict:
    """
    Update telemetry state per device.
    Mendukung format flat dari firmware/simulator (tilt_x, tilt_y, tilt, sway, wind_speed_kn)
    serta format nested (sensors -> axes).
    """
    state = DEVICE_CACHE.setdefault(device_id, {
        'device_id': device_id,
        'wind_speed': 0.0,
        'wind_speed_ms': 0.0,
        'pitch': 0.0,
        'roll': 0.0,
        'tilt_rate': 0.0,
        'sway': 0.0,
        'total_tilt': 0.0,
        'indikator': 'tolerance',
    })

    if not isinstance(payload, dict):
        return state

    # 1. Format nested jika ada sensors.axes
    if 'sensors' in payload:
        sensors = payload.get('sensors', {})
        axes = sensors.get('axes', {})
        ws = sensors.get('wind_speed_knot') or sensors.get('wind_speed')
        if ws is not None:
            state['wind_speed'] = float(ws)
        ws_ms = sensors.get('wind_speed_ms')
        if ws_ms is not None:
            state['wind_speed_ms'] = float(ws_ms)
        if axes.get('pitch') is not None:
            state['pitch'] = float(axes['pitch'])
        if axes.get('roll') is not None:
            state['roll'] = float(axes['roll'])
        if axes.get('tilt_rate') is not None:
            state['tilt_rate'] = float(axes['tilt_rate'])
        if axes.get('total_tilt') is not None:
            state['total_tilt'] = float(axes['total_tilt'])
        if sensors.get('sway') is not None:
            state['sway'] = float(sensors['sway'])
        if 'indikator' in payload:
            state['indikator'] = str(payload['indikator']).lower()
        return state

    # 2. Format Flat (Firmware ESP32 / Simulator)
    # TILT: jika topik memuat /tilt atau payload memuat tilt/tilt_x/pitch
    if 'tilt' in topic or 'tilt' in payload or 'tilt_x' in payload or 'pitch' in payload:
        tilt_x = payload.get('tilt_x')
        tilt_y = payload.get('tilt_y')
        tilt = payload.get('tilt')
        sway = payload.get('sway')
        status = payload.get('status') or payload.get('indikator')

        if tilt_x is not None:
            state['pitch'] = float(tilt_x)
        elif payload.get('pitch') is not None:
            state['pitch'] = float(payload['pitch'])

        if tilt_y is not None:
            state['roll'] = float(tilt_y)
        elif payload.get('roll') is not None:
            state['roll'] = float(payload['roll'])

        if tilt is not None:
            state['total_tilt'] = float(tilt)
        elif payload.get('total_tilt') is not None:
            state['total_tilt'] = float(payload['total_tilt'])

        if sway is not None:
            state['sway'] = float(sway)

        if status:
            norm_status = str(status).strip().lower()
            state['indikator'] = 'intolerance' if 'intol' in norm_status else 'tolerance'

    # WIND: jika topik memuat /wind atau payload memuat info angin
    if 'wind' in topic or 'wind_speed_ms' in payload or 'wind_speed_kn' in payload or 'wind_speed' in payload:
        ws_kn = payload.get('wind_speed_kn') or payload.get('wind_speed_knot') or payload.get('wind_speed')
        ws_ms = payload.get('wind_speed_ms')

        if ws_kn is not None:
            state['wind_speed'] = float(ws_kn)
        elif ws_ms is not None:
            state['wind_speed'] = round(float(ws_ms) * 1.94384, 2)

        if ws_ms is not None:
            state['wind_speed_ms'] = float(ws_ms)
        elif ws_kn is not None:
            state['wind_speed_ms'] = round(float(ws_kn) / 1.94384, 2)

    return state


class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for Structural Health Monitoring (Verticality).'

    def handle(self, *args, **options):
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="shm_backend_subscriber"
            )
        except AttributeError:
            client = mqtt.Client(client_id="shm_backend_subscriber")

        # MQTT credentials & topics
        broker_host = getattr(settings, 'MQTT_SERVER', 'emqx.nayakanms.com')
        broker_port = int(getattr(settings, 'MQTT_PORT', 1884))
        broker_user = getattr(settings, 'MQTT_USER', 'nyk_ws')
        broker_pass = getattr(settings, 'MQTT_PASSWORD', 'ws')
        topic_tilt = getattr(settings, 'MQTT_TOPIC_TILT', 'nms/E32_VER_WEES/vertical/tilt')
        topic_wind = getattr(settings, 'MQTT_TOPIC_WIND', 'nms/E32_VER_WEES/vertical/wind')

        client.username_pw_set(broker_user, broker_pass)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT VERTICALITY LISTENER - Structural Health Monitoring"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  ✓ Connected to broker: {broker_host}:{broker_port}")

                sub_topics = [
                    (topic_tilt, 1),
                    (topic_wind, 1),
                    ("nms/E32_VER_WEES/vertical/#", 1),
                    ("nms/E32_VER_WS/vertical/#", 1),
                    ("nms/+/vertical/tilt", 1),
                    ("nms/+/vertical/wind", 1),
                    ("nms/+/vertical/#", 1),
                ]
                seen = set()
                unique_topics = []
                for t, qos in sub_topics:
                    if t and t not in seen:
                        seen.add(t)
                        unique_topics.append((t, qos))

                client.subscribe(unique_topics)
                for t, _ in unique_topics:
                    self.stdout.write(f"  ✓ Subscribed to: {t}")
                self.stdout.write(self.style.SUCCESS("=" * 60))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Connection failed with code: {reason_code}"))

        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 📥 Message on {topic}")

                device_id = extract_device_id(topic, payload)
                parsed = update_device_telemetry(device_id, topic, payload)

                # Simpan ke SensorData untuk device_id yang terdeteksi
                SensorData.objects.create(
                    device_id=device_id,
                    wind_speed=parsed['wind_speed'],
                    wind_speed_ms=parsed['wind_speed_ms'],
                    pitch=parsed['pitch'],
                    roll=parsed['roll'],
                    tilt_rate=parsed['tilt_rate'],
                    sway=parsed['sway'],
                    total_tilt=parsed['total_tilt'],
                    indikator=parsed['indikator']
                )

                # Mirror alias: jika data datang untuk E32_VER_WEES, mirror juga untuk E32_VER_WS (dan sebaliknya)
                if device_id == 'E32_VER_WEES':
                    SensorData.objects.create(
                        device_id='E32_VER_WS',
                        wind_speed=parsed['wind_speed'],
                        wind_speed_ms=parsed['wind_speed_ms'],
                        pitch=parsed['pitch'],
                        roll=parsed['roll'],
                        tilt_rate=parsed['tilt_rate'],
                        sway=parsed['sway'],
                        total_tilt=parsed['total_tilt'],
                        indikator=parsed['indikator']
                    )
                elif device_id == 'E32_VER_WS':
                    SensorData.objects.create(
                        device_id='E32_VER_WEES',
                        wind_speed=parsed['wind_speed'],
                        wind_speed_ms=parsed['wind_speed_ms'],
                        pitch=parsed['pitch'],
                        roll=parsed['roll'],
                        tilt_rate=parsed['tilt_rate'],
                        sway=parsed['sway'],
                        total_tilt=parsed['total_tilt'],
                        indikator=parsed['indikator']
                    )

                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Data saved: Site {device_id}, Wind: {parsed['wind_speed']} knot, Tilt: {parsed['total_tilt']}°"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing message: {e}"))

        client.on_connect = on_connect
        client.on_message = on_message

        self.stdout.write(f"Connecting to broker {broker_host}:{broker_port}...")
        try:
            client.connect(broker_host, broker_port, 60)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Connection error: {e}"))
            return

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nDisconnecting...")
            client.disconnect()
            self.stdout.write("Disconnected.")
