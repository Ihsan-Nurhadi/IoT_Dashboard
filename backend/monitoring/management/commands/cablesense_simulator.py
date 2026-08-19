import time
import json
import random
import math
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Starts the MQTT publisher simulator for Cable Sense Health Telemetry.'

    def handle(self, *args, **options):
        broker_host = "broker.emqx.io"
        broker_port = 1883
        topic = "cablesense/telemetry"

        client_uniq_id = f"cablesense_simulator_{random.randint(1000, 9999)}"
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_uniq_id
            )
        except AttributeError:
            client = mqtt.Client(client_id=client_uniq_id)

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  MQTT CABLE SENSE SIMULATOR - Live Telemetry Generator"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Connecting to broker: {broker_host}:{broker_port}")
        
        try:
            client.connect(broker_host, broker_port, 60)
            client.loop_start()
            self.stdout.write(self.style.SUCCESS("  [OK] Connected & Loop Started."))
            self.stdout.write(self.style.SUCCESS("=" * 60))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Connection failed: {e}"))
            return

        # Simulation states
        device_id = "Cable_Sense_01"
        is_cut = False
        loop_counter = 0

        try:
            while True:
                loop_counter += 1
                
                # Base trends using sine waves for temperature
                time_factor = time.time() / 120.0  # Slow wave
                base_temp = 28.0 + 3.0 * math.sin(time_factor)
                temperature = round(base_temp + random.uniform(-0.3, 0.3), 1)

                # Vibration: usually low, occasionally spikes
                if random.random() < 0.08:
                    vibration = round(random.uniform(0.3, 0.75), 3)  # high wind or movement spike
                else:
                    vibration = round(random.uniform(0.01, 0.04), 3)

                # Tension: fluctuates slightly around 100%
                tension = round(100.0 + 2.0 * math.sin(time_factor * 0.7) + random.uniform(-0.4, 0.4), 1)

                # Impact: usually 0, occasionally a transient hit
                if random.random() < 0.04:
                    impact = round(random.uniform(0.8, 3.2), 2)
                else:
                    impact = 0.0

                # Check status
                device_status = "Normal"
                if is_cut:
                    device_status = "Critical"
                elif vibration > 0.6 or tension < 92.0 or tension > 108.0 or temperature > 38.0:
                    device_status = "Warning"

                # Signal Strength (RSSI): fluctuating between -55 and -69
                signal_strength = random.randint(-68, -56)
                is_connected = True

                payload = {
                    "device_id": device_id,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "vibration": vibration,
                    "tension": tension,
                    "impact": impact,
                    "is_cut": is_cut,
                    "temperature": temperature,
                    "device_status": device_status,
                    "signal_strength": signal_strength,
                    "is_connected": is_connected
                }

                payload_str = json.dumps(payload)
                self.stdout.write(f"[{datetime.now():%H:%M:%S}] [PUB] {payload_str}")
                client.publish(topic, payload_str)

                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write("\nStopping simulator...")
            client.loop_stop()
            client.disconnect()
            self.stdout.write("Simulator stopped.")
