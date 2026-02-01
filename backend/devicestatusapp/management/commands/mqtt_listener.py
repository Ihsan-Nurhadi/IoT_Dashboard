import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from devicestatusapp.models import DeviceState
from django.utils import timezone
from django.db import close_old_connections
import pytz # Import library timezone

class Command(BaseCommand):
    help = 'Listens for MQTT messages'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = int(settings.MQTT_PORT)
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD
        TOPIC = settings.MQTT_TOPIC_DATA 

        # Setup Timezone Jakarta
        jkt_tz = pytz.timezone('Asia/Jakarta')

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"Connected! Subscribing to {TOPIC}"))
                client.subscribe(TOPIC)
            else:
                self.stdout.write(self.style.ERROR(f"Connection failed: {rc}"))

        def on_message(client, userdata, msg):
            close_old_connections()
            try:
                payload_str = msg.payload.decode()
                payload = json.loads(payload_str)
                data_obj = payload.get("data", {})
                
                # Ambil waktu sekarang (Aware Timezone)
                now_utc = timezone.now()
                # Konversi ke Jakarta untuk Log
                now_jkt = now_utc.astimezone(jkt_tz)

                # --- 1. PROSES STATUS PINTU ---
                door_status = data_obj.get("door")
                if door_status:
                    # RAHASIA AGAR JAM BERUBAH:
                    # Masukkan field timestamp/updated_at ke dalam 'defaults'
                    # Ini memaksa Django meng-update kolom waktu meskipun statusnya sama
                    obj, created = DeviceState.objects.update_or_create(
                        device_name="Door Panel",
                        defaults={
                            'status': door_status,
                            'last_updated': now_utc # Pastikan nama field ini sesuai di models.py
                        }
                    )
                    # Print log dengan jam Jakarta
                    self.stdout.write(f"Updated Door: {door_status} at {now_jkt.strftime('%Y-%m-%d %H:%M:%S')}")

                # --- 2. PROSES STATUS PLN ---
                pln_status = data_obj.get("pln")
                if pln_status:
                    final_pln = "Active" if pln_status == "ON" else "Inactive"
                    
                    obj, created = DeviceState.objects.update_or_create(
                        device_name="PLN",
                        defaults={
                            'status': final_pln,
                            'last_updated': now_utc # Paksa update waktu
                        }
                    )
                    self.stdout.write(f"Updated PLN: {final_pln} at {now_jkt.strftime('%Y-%m-%d %H:%M:%S')}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))

        client = mqtt.Client()
        if USER and PASSWORD:
            client.username_pw_set(USER, PASSWORD)
            
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            self.stdout.write(f"Connecting to {BROKER}...")
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error: {e}"))