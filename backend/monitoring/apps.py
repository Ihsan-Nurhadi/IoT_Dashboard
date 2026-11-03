from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Structural Health Monitoring'

    def ready(self):
        import os
        import sys

        # Cegah double execution saat django development runserver
        is_runserver = any('runserver' in arg for arg in sys.argv)
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        # Lewati eksekusi saat perintah migration / command build
        cmd = sys.argv[1] if len(sys.argv) > 1 else ''
        if cmd in ('migrate', 'makemigrations', 'collectstatic', 'check', 'shell'):
            return

        # Monitoring 30-menit site verticality E32_VER_WEES dinonaktifkan.
        # Digantikan dengan background audit scheduler untuk perangkat testing (E32_IPS_7) tiap 30 menit.
        try:
            from .speaker_audit_monitor import start_speaker_audit_scheduler
            start_speaker_audit_scheduler()
        except Exception as e:
            print(f"[SPEAKER AUDIT SCHEDULER START ERROR] {e}", flush=True)
