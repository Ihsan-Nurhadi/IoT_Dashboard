import json
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from monitoring.models import SensorData

def parse_payload(payload):
    """
    Parse payload dari format baru (nested) atau lama (flat).
    """
    if 'sensors' in payload:
        sensors = payload.get('sensors', {})
        axes = sensors.get('axes', {})
        return {
            'device_id': payload.get('device_id', 'UNKNOWN'),
            'wind_speed': sensors.get('wind_speed_knot') or sensors.get('wind_speed') or 0.0,
            'wind_speed_ms': sensors.get('wind_speed_ms') or 0.0,
            'pitch': axes.get('pitch') or 0.0,
            'roll': axes.get('roll') or 0.0,
            'tilt_rate': axes.get('tilt_rate') or 0.0,
            'total_tilt': axes.get('total_tilt') or 0.0,
            'sway': sensors.get('sway') or 0.0,
            'indikator': payload.get('indikator', 'tolerance'),
        }
    else:
        return {
            'device_id': payload.get('device_id', 'DPK'),
            'wind_speed': payload.get('wind_speed_knot') or payload.get('wind_speed') or 0.0,
            'wind_speed_ms': payload.get('wind_speed_ms') or 0.0,
            'pitch': payload.get('pitch') or 0.0,
            'roll': payload.get('roll') or 0.0,
            'tilt_rate': payload.get('tilt_rate') or 0.0,
            'total_tilt': payload.get('total_tilt') or 0.0,
            'sway': payload.get('sway') or 0.0,
            'indikator': payload.get('indikator', 'tolerance'),
        }

class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for Structural Health Monitoring (Verticality).'

    def handle(self, *args, **options):
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="shm_backend_subscriber"
        )
        
        # Use settings from django_mqtt settings.py
        # Since settings matches Whitebox EMQX details, we map it to standard server configurations
        broker_host = getattr(settings, 'MQTT_SERVER', 'emqx.nayakanms.com')
        broker_port = getattr(settings, 'MQTT_PORT', 1884)
        broker_user = getattr(settings, 'MQTT_USER', 'nyk_ws')
        broker_pass = getattr(settings, 'MQTT_PASSWORD', 'ws')
        topic_tilt = getattr(settings, 'MQTT_TOPIC_TILT', 'nms/E32_VER_WS/vertical/tilt')
        topic_wind = getattr(settings, 'MQTT_TOPIC_WIND', 'nms/E32_VER_WS/vertical/wind')

        client.username_pw_set(broker_user, broker_pass)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT VERTICALITY LISTENER - Structural Health Monitoring"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  ✓ Connected to broker: {broker_host}:{broker_port}")
                self.stdout.write(f"  ✓ Subscribing to tilt topic: {topic_tilt}")
                self.stdout.write(f"  ✓ Subscribing to wind topic: {topic_wind}")
                self.stdout.write(self.style.SUCCESS("=" * 60))
                client.subscribe([(topic_tilt, 1), (topic_wind, 1)])
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Connection failed with code: {reason_code}"))

        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 📥 Message on {topic}")
                
                parsed = parse_payload(payload)
                
                # Save to DB
                SensorData.objects.create(
                    device_id=parsed['device_id'],
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
                    f"  ✓ Data saved: Site {parsed['device_id']}, Wind: {parsed['wind_speed']} knot, Tilt: {parsed['total_tilt']}°"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing message: {e}"))

        client.on_connect = on_connect
        client.on_message = on_message

        self.stdout.write(f"Connecting to broker {broker_host}...")
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
