import json
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.conf import settings
from devicestatusapp.models import DeviceState
from django.utils import timezone  # [PENTING] Untuk waktu realtime
from django.db import close_old_connections # [PENTING] Untuk mencegah DB disconnect

class Command(BaseCommand):
    help = 'Listens for MQTT messages for Door and PLN'

    def handle(self, *args, **kwargs):
        BROKER = settings.MQTT_SERVER
        PORT = int(settings.MQTT_PORT) # Pastikan jadi integer
        USER = settings.MQTT_USER
        PASSWORD = settings.MQTT_PASSWORD
        TOPIC = settings.MQTT_TOPIC_DATA 

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.stdout.write(self.style.SUCCESS(f"Connected! Subscribing to {TOPIC}"))
                client.subscribe(TOPIC)
            else:
                self.stdout.write(self.style.ERROR(f"Connection failed: {rc}"))

        def on_message(client, userdata, msg):
            # [FIX 1] Reset koneksi DB setiap kali terima pesan
            # Ini wajib untuk script long-running agar tidak kena error "MySQL server has gone away"
            close_old_connections()

            try:
                payload_str = msg.payload.decode()
                payload = json.loads(payload_str)
                data_obj = payload.get("data", {})
                
                # [FIX 2] Ambil waktu sekarang untuk paksa update
                current_now = timezone.now()

                # --- 1. PROSES STATUS PINTU ---
                door_status = data_obj.get("door")
                if door_status:
                    DeviceState.objects.update_or_create(
                        device_name="Door Panel",
                        defaults={
                            'status': door_status,
                            # [FIX 3] Masukkan field timestamp ke defaults
                            # Pastikan nama field ini sesuai models.py Anda (misal: updated_at, timestamp, atau last_updated)
                            'updated_at': current_now 
                        }
                    )
                    self.stdout.write(f"Updated Door: {door_status} at {current_now}")

                # --- 2. PROSES STATUS PLN ---
                pln_status = data_obj.get("pln")
                if pln_status:
                    final_pln = "Active" if pln_status == "ON" else "Inactive"
                    
                    DeviceState.objects.update_or_create(
                        device_name="PLN",
                        defaults={
                            'status': final_pln,
                            # [FIX 3] Masukkan field timestamp disini juga
                            'updated_at': current_now
                        }
                    )
                    self.stdout.write(f"Updated PLN: {final_pln} at {current_now}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing message: {e}"))

        client = mqtt.Client()
        # Set username password hanya jika ada di settings
        if USER and PASSWORD:
            client.username_pw_set(USER, PASSWORD)
            
        client.on_connect = on_connect
        client.on_message = on_message

        try:
            self.stdout.write(f"Connecting to {BROKER}:{PORT}...")
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Connection Error: {e}"))