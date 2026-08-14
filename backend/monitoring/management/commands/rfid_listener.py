import json
import random
import paho.mqtt.client as mqtt
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from monitoring.models import RFIDScan, RegisteredRFIDTag, RegisteredRFIDReader
from zoneinfo import ZoneInfo

class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for RFID Asset Monitoring at Tower Landing Page.'

    def handle(self, *args, **options):
        # Configuration parameters
        broker_host = "broker.emqx.io"
        broker_port = 1883
        topic = "rfid/scan/log"
        jakarta_tz = ZoneInfo('Asia/Jakarta')

        client_uniq_id = f"rfid_asset_subscriber_{random.randint(1000, 9999)}"
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
                self.stdout.write(self.style.SUCCESS("  MQTT RFID ASSET LISTENER - Landing Page RFID"))
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
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [IN] RFID Message: {payload_str}")
                
                # Payload format:
                # {"timestamp": "2026-08-12 16:03:21", "reader_id": "Raspi_RFID_Reader_01", "tag_epc": "E2 80 68 94 00 00 50 16 8D 43 38 62"}
                timestamp_str = payload.get('timestamp')
                reader_id = payload.get('reader_id', 'Raspi_RFID_Reader_01')
                tag_epc = payload.get('tag_epc')

                if not tag_epc:
                    self.stdout.write(self.style.WARNING("  [WARN] Missing tag_epc in payload. Skipping."))
                    return

                # Parse timestamp or fallback to server time
                if timestamp_str:
                    try:
                        naive_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = timezone.make_aware(naive_dt, jakarta_tz)
                    except Exception as parse_err:
                        self.stdout.write(self.style.WARNING(f"  [WARN] Timestamp parsing error: {parse_err}. Using server time."))
                        timestamp = timezone.now()
                else:
                    timestamp = timezone.now()

                # Whitelist checks
                # 1. Tag Whitelist Check: Tag MUST be registered in Admin Whitelist
                tag_registered = RegisteredRFIDTag.objects.filter(tag_epc__iexact=tag_epc, is_active=True).exists()
                if not tag_registered:
                    self.stdout.write(self.style.WARNING(
                        f"  [IGNORE] Discarding scan: Tag {tag_epc} is NOT registered in Admin Whitelist."
                    ))
                    return

                # 2. Reader Auto-Registration & Check: Auto-register new reader ID so admin can see and custom name it in Admin Dashboard
                reader_obj, created = RegisteredRFIDReader.objects.get_or_create(
                    reader_id=reader_id,
                    defaults={'name': f"Reader ({reader_id})", 'is_active': True}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(
                        f"  [NEW READER] Registered new Reader ID automatically: {reader_id}"
                    ))

                if not reader_obj.is_active:
                    self.stdout.write(self.style.WARNING(
                        f"  [IGNORE] Discarding scan: Reader {reader_id} is disabled in Admin."
                    ))
                    return

                # Log scan to DB
                RFIDScan.objects.create(
                    timestamp=timestamp,
                    reader_id=reader_id,
                    tag_epc=tag_epc
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] RFID Scan Saved: Tag {tag_epc} by Reader {reader_id}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [FAIL] Error processing RFID message: {e}"))

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
