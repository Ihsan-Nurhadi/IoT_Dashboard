import json
import paho.mqtt.client as mqtt
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from monitoring.models import SensorReading

class Command(BaseCommand):
    help = 'Starts the MQTT subscriber daemon for Air Quality Monitoring System (AQMS).'

    def handle(self, *args, **options):
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="aqms_backend_subscriber"
            )
        except AttributeError:
            client = mqtt.Client(client_id="aqms_backend_subscriber")
        
        # Use settings from django_mqtt settings.py
        broker_host = getattr(settings, 'MQTT_SERVER', 'emqx.nayakanms.com')
        broker_port = getattr(settings, 'MQTT_PORT', 1884)
        broker_user = getattr(settings, 'MQTT_USER', 'nyk_ws')
        broker_pass = getattr(settings, 'MQTT_PASSWORD', 'ws')
        topic = getattr(settings, 'MQTT_TOPIC_AQMS', 'wqx/E32_WS/data')

        client.username_pw_set(broker_user, broker_pass)

        def on_connect(client, userdata, flags, rc, *args, **kwargs):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(self.style.SUCCESS("  MQTT AQMS LISTENER - Air Quality Monitoring System"))
                self.stdout.write(self.style.SUCCESS("=" * 60))
                self.stdout.write(f"  [OK] Connected to broker: {broker_host}:{broker_port}")
                self.stdout.write(f"  [OK] Subscribing to topic: {topic}")
                self.stdout.write(self.style.SUCCESS("=" * 60))
                client.subscribe(topic)
            else:
                self.stdout.write(self.style.ERROR(f"  [ERROR] Connection failed with code: {rc}"))

        def on_message(client, userdata, msg):
            try:
                payload_str = msg.payload.decode('utf-8')
                payload = json.loads(payload_str)
                self.stdout.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [MSG] Message on {msg.topic}")
                
                # Extract parameters mapping directly to physical sensor specs
                suhu = float(payload.get("suhu", 0.0))
                kelembapan = float(payload.get("kelembapan", 0.0))
                tekanan = float(payload.get("tekanan", 0.0))
                kecepatan_angin = float(payload.get("kecepatan_angin", 0.0))
                arah_angin = float(payload.get("arah_angin", 0.0))
                curah_hujan = float(payload.get("curah_hujan", 0.0))
                cahaya = float(payload.get("cahaya", 0.0))
                radiasi = float(payload.get("radiasi", 0.0))
                pm25 = float(payload.get("pm25", 0.0))
                pm10 = float(payload.get("pm10", 0.0))
                ion_negatif = float(payload.get("ion_negatif", 0.0))
                noise = float(payload.get("noise", 0.0))

                # Save to DB
                SensorReading.objects.create(
                    node_id="E32_WS (Sector A)",
                    temperature=suhu,
                    humidity=kelembapan,
                    pressure=tekanan,
                    wind_speed=kecepatan_angin,
                    wind_direction=arah_angin,
                    rain=curah_hujan,
                    light=cahaya,
                    radiation=radiasi,
                    pm25=pm25,
                    pm10=pm10,
                    negative_ion=ion_negatif,
                    noise=noise
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  [OK] Data saved: Suhu={suhu} degC, Lembap={kelembapan}%, PM2.5={pm25}"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  [ERROR] Error processing message: {e}"))

        client.on_connect = on_connect
        client.on_message = on_message

        self.stdout.write(f"Connecting to broker {broker_host}...")
        try:
            client.connect(broker_host, broker_port, 60)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [ERROR] Connection error: {e}"))
            return

        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write("\nDisconnecting...")
            client.disconnect()
            self.stdout.write("Disconnected.")
