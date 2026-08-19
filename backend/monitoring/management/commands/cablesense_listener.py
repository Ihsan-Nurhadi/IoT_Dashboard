import json
import random
import paho.mqtt.client as mqtt
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from monitoring.models import CableHealthTelemetry
from zoneinfo import ZoneInfo

class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for Cable Sense Health Monitoring.'

    def handle(self, *args, **options):
        # Configuration parameters
        broker_host = "broker.emqx.io"
        broker_port = 1883
        topic = "cablesense/telemetry"
        jakarta_tz = ZoneInfo('Asia/Jakarta')

        client_uniq_id = f"cablesense_subscriber_{random.randint(1000, 9999)}"
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_uniq_id
            )
        except AttributeError:
            client = mqtt.Client(client_id=client_uniq_id)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT CABLE SENSE LISTENER - Telemetry Monitoring"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  [OK] Connected to broker: {broker_host}:{broker_port}")
                self.stdout.write(f"  [OK] Subscribing to topic: {topic}")
                self.stdout.write(self.style.SUCCESS("=" * 60))
                client.subscribe(topic)
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Connection failed with code: {reason_code}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [IN] Cable Sense Message: {payload_str}")
                
                device_id = payload.get('device_id', 'Cable_Sense_01')
                vibration = float(payload.get('vibration', 0.0))
                tension = float(payload.get('tension', 100.0))
                impact = float(payload.get('impact', 0.0))
                is_cut = bool(payload.get('is_cut', False))
                temperature = float(payload.get('temperature', 25.0))
                device_status = payload.get('device_status', 'Normal')
                signal_strength = int(payload.get('signal_strength', -60))
                is_connected = bool(payload.get('is_connected', True))

                # Log to DB
                CableHealthTelemetry.objects.create(
                    device_id=device_id,
                    vibration=vibration,
                    tension=tension,
                    impact=impact,
                    is_cut=is_cut,
                    temperature=temperature,
                    device_status=device_status,
                    signal_strength=signal_strength,
                    is_connected=is_connected
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] Saved CableHealth: {device_id} - Vibration: {vibration}, Tension: {tension}, Temp: {temperature}, Cut: {is_cut}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Error processing Cable Sense message: {e}"))

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
