import json
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from monitoring.models import SensorData

DEVICE_ID = 'E32_VER_WEES'
TOPIC_TILT = 'nms/E32_VER_WEES/vertical/tilt'
TOPIC_WIND = 'nms/E32_VER_WEES/vertical/wind'

# State telemetry in-memory cache untuk E32_VER_WEES
STATE = {
    'device_id': DEVICE_ID,
    'wind_speed': 0.0,
    'wind_speed_ms': 0.0,
    'pitch': 0.0,
    'roll': 0.0,
    'tilt_rate': 0.0,
    'sway': 0.0,
    'total_tilt': 0.0,
    'indikator': 'tolerance',
}


def process_message(topic: str, payload: dict) -> dict:
    """
    Memproses parameter sesuai spesifikasi:
    - nms/E32_VER_WEES/vertical/wind: {"ip":"...","ts":...,"wind_speed_ms":0,"wind_speed_kn":0}
    - nms/E32_VER_WEES/vertical/tilt: {"ip":"...","ts":...,"tilt_x":0,"tilt_y":0,"tilt":0,"tilt_tol":0.286,"sway":0,"sway_tol":210,"status":"TOLERANCE"}
    """
    if not isinstance(payload, dict):
        return STATE

    # 1. Pesan TILT
    if 'tilt' in topic or 'tilt_x' in payload or 'tilt' in payload:
        tilt_x = payload.get('tilt_x')
        tilt_y = payload.get('tilt_y')
        tilt = payload.get('tilt')
        sway = payload.get('sway')
        status = payload.get('status') or payload.get('indikator') or 'TOLERANCE'

        if tilt_x is not None:
            STATE['pitch'] = float(tilt_x)
        if tilt_y is not None:
            STATE['roll'] = float(tilt_y)
        if tilt is not None:
            STATE['total_tilt'] = float(tilt)
        if sway is not None:
            STATE['sway'] = float(sway)

        norm_status = str(status).strip().upper()
        STATE['indikator'] = 'tolerance' if norm_status == 'TOLERANCE' else 'intolerance'

    # 2. Pesan WIND
    if 'wind' in topic or 'wind_speed_kn' in payload or 'wind_speed_ms' in payload:
        ws_kn = payload.get('wind_speed_kn')
        ws_ms = payload.get('wind_speed_ms')

        if ws_kn is not None:
            STATE['wind_speed'] = float(ws_kn)
        elif ws_ms is not None:
            STATE['wind_speed'] = round(float(ws_ms) * 1.94384, 2)

        if ws_ms is not None:
            STATE['wind_speed_ms'] = float(ws_ms)
        elif ws_kn is not None:
            STATE['wind_speed_ms'] = round(float(ws_kn) / 1.94384, 2)

    return STATE


class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for E32_VER_WEES Verticality.'

    def handle(self, *args, **options):
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="verticality_wees_subscriber"
            )
        except AttributeError:
            client = mqtt.Client(client_id="verticality_wees_subscriber")

        broker_host = getattr(settings, 'MQTT_SERVER', 'emqx.nayakanms.com')
        broker_port = int(getattr(settings, 'MQTT_PORT', 1884))
        broker_user = getattr(settings, 'MQTT_USER', 'nyk_ws')
        broker_pass = getattr(settings, 'MQTT_PASSWORD', 'ws')

        client.username_pw_set(broker_user, broker_pass)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT VERTICALITY LISTENER (E32_VER_WEES)"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  ✓ Connected to broker: {broker_host}:{broker_port}")
                self.stdout.write(f"  ✓ Subscribing to: {TOPIC_TILT} (QoS 0)")
                self.stdout.write(f"  ✓ Subscribing to: {TOPIC_WIND} (QoS 0)")
                self.stdout.write(self.style.SUCCESS("=" * 60))

                client.subscribe([
                    (TOPIC_TILT, 0),
                    (TOPIC_WIND, 0),
                ])
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Connection failed with code: {reason_code}"))

        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 📥 Message on {topic}: {payload_str}")

                parsed = process_message(topic, payload)

                # Simpan HANYA untuk site E32_VER_WEES
                SensorData.objects.create(
                    device_id=DEVICE_ID,
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
                    f"  ✓ Saved: Site={DEVICE_ID} | Tilt={parsed['total_tilt']}° (X={parsed['pitch']}, Y={parsed['roll']}) | Sway={parsed['sway']}mm | Wind={parsed['wind_speed']} knot ({parsed['wind_speed_ms']} m/s) | Status={parsed['indikator']}"
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
