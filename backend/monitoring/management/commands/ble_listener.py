import json
import paho.mqtt.client as mqtt
from datetime import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from monitoring.models import BLEScan

class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for BLE Asset Monitoring.'

    def handle(self, *args, **options):
        # Configuration parameters
        broker_host = "broker.emqx.io"
        broker_port = 1883
        broker_user = "nyk_ws"
        broker_pass = "ws"
        topic = "BLE-TEST"

        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="ble_asset_subscriber"
            )
        except AttributeError:
            client = mqtt.Client(client_id="ble_asset_subscriber")

        client.username_pw_set(broker_user, broker_pass)

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT BLE ASSET LISTENER - Antenna Monitoring"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  ✓ Connected to broker: {broker_host}:{broker_port}")
                self.stdout.write(f"  ✓ Subscribing to topic: {topic}")
                self.stdout.write(self.style.SUCCESS("=" * 60))
                client.subscribe(topic)
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Connection failed with code: {reason_code}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] 📥 Message on {msg.topic}")
                
                # Payload format:
                # {"Sensor1":[{"date":"06/08/2026 09:50:54","mac":"7C:D9:F4:03:32:47","name":"BTSID TII","rssi":-70,"data":"..."}]}
                for sensor_key in payload:
                    scans = payload[sensor_key]
                    if not isinstance(scans, list):
                        continue
                    
                    for scan in scans:
                        date_str = scan.get('date')
                        mac = scan.get('mac')
                        name = scan.get('name')
                        rssi = scan.get('rssi', 0)
                        raw_data = scan.get('data', '{}')
                        
                        try:
                            naive_dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                            timestamp = timezone.make_aware(naive_dt)
                        except ValueError:
                            timestamp = timezone.now()
                            
                        # Parse Eddystone nested data
                        uuid = None
                        namespace_id = None
                        instance_id = None
                        power = None
                        
                        try:
                            inner_data = json.loads(raw_data)
                            uuid = inner_data.get('UUID')
                            namespace_id = inner_data.get('Namespace ID')
                            instance_id = inner_data.get('Instance ID')
                            power = inner_data.get('power')
                        except Exception:
                            pass
                            
                        # Log scan
                        BLEScan.objects.create(
                            timestamp=timestamp,
                            mac=mac,
                            name=name,
                            rssi=rssi,
                            uuid=uuid,
                            namespace_id=namespace_id,
                            instance_id=instance_id,
                            power=power
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✓ BLE Saved: {name} ({mac}) - RSSI: {rssi} dBm"
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
