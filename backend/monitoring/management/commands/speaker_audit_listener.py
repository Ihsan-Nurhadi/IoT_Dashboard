import time
from django.core.management.base import BaseCommand
from monitoring.speaker_audit_monitor import (
    run_speaker_health_audit,
    start_speaker_audit_scheduler,
    BROKER_HOST,
    BROKER_PORT,
    MQTT_USER,
    MQTT_PASS,
    DEVICE_ID,
    AUDIT_TOPIC,
    DEFAULT_PAYLOAD,
    AUDIT_TIMEOUT_SECONDS,
)


class Command(BaseCommand):
    help = 'Starts the MQTT health audit & listener for the testing speaker device (E32_IPS_7).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Jalankan pengecekan 1 kali saja sekarang juga (tanpa loop 30 menit).',
        )
        parser.add_argument(
            '--device',
            type=str,
            default=DEVICE_ID,
            help=f'Device ID perangkat testing (default: {DEVICE_ID})',
        )
        parser.add_argument(
            '--topic',
            type=str,
            default=AUDIT_TOPIC,
            help=f'Topic audit (default: {AUDIT_TOPIC})',
        )
        parser.add_argument(
            '--payload',
            type=str,
            default=DEFAULT_PAYLOAD,
            help=f'Payload audit JSON (default: {DEFAULT_PAYLOAD})',
        )
        parser.add_argument(
            '--timeout',
            type=float,
            default=AUDIT_TIMEOUT_SECONDS,
            help=f'Batas waktu timeout respon dalam detik (default: {AUDIT_TIMEOUT_SECONDS})',
        )
        parser.add_argument(
            '--broker',
            type=str,
            default=BROKER_HOST,
            help=f'MQTT Broker host (default: {BROKER_HOST})',
        )
        parser.add_argument(
            '--port',
            type=int,
            default=BROKER_PORT,
            help=f'MQTT Broker port (default: {BROKER_PORT})',
        )
        parser.add_argument(
            '--user',
            type=str,
            default=MQTT_USER,
            help=f'MQTT Username (default: {MQTT_USER})',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=MQTT_PASS,
            help=f'MQTT Password (default: {MQTT_PASS})',
        )
        parser.add_argument(
            '--gsheet-url',
            type=str,
            default='',
            help='URL Webhook Google Apps Script khusus spreadsheet speaker (terpisah dari verticality)',
        )

    def handle(self, *args, **options):
        once = options.get('once')
        device_id = options.get('device')
        audit_topic = options.get('topic')
        payload_str = options.get('payload')
        timeout_sec = options.get('timeout')
        broker = options.get('broker')
        port = options.get('port')
        user = options.get('user')
        password = options.get('password')
        gsheet_url = options.get('gsheet_url')

        self.stdout.write(self.style.SUCCESS("=" * 65))
        self.stdout.write(self.style.SUCCESS(f"  SPEAKER AUDIT & HEALTH LISTENER ({device_id})"))
        self.stdout.write(self.style.SUCCESS("=" * 65))
        self.stdout.write(f"  • Broker        : {broker}:{port}")
        self.stdout.write(f"  • User          : {user}")
        self.stdout.write(f"  • Audit Topic   : {audit_topic}")
        self.stdout.write(f"  • Audit Payload : {payload_str}")
        self.stdout.write(f"  • Timeout       : {timeout_sec}s")
        self.stdout.write(f"  • GSheet Webhook: {gsheet_url or '(via SPEAKER_GSHEET_WEBHOOK_URL env)'}")
        self.stdout.write(f"  • Mode          : {'Single Check (--once)' if once else 'Recurring 30-Minute Daemon'}")
        self.stdout.write(self.style.SUCCESS("=" * 65))

        if once:
            res = run_speaker_health_audit(
                broker=broker,
                port=port,
                user=user,
                password=password,
                device_id=device_id,
                audit_topic=audit_topic,
                payload_str=payload_str,
                timeout_sec=timeout_sec,
                gsheet_url=gsheet_url,
            )
            if res.get("is_alive"):
                self.stdout.write(self.style.SUCCESS(f"[RESULT] Perangkat {device_id} ALIVE / ONLINE (Latency: {res.get('latency_seconds')}s)"))
            else:
                self.stdout.write(self.style.WARNING(f"[RESULT] Perangkat {device_id} DEAD / OFFLINE (No response within {timeout_sec}s)"))
            return

        # Continuous daemon mode
        start_speaker_audit_scheduler()
        self.stdout.write(self.style.SUCCESS("[DAEMON] Scheduler audit aktif. Menjalankan thread loop..."))
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.NOTICE("\n[DAEMON] Menghentikan speaker audit listener..."))

