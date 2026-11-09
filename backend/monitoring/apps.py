from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Structural Health Monitoring'

    def ready(self):
        import os
        import sys

        # Cegah eksekusi ganda jika dipanggil via management command CLI (misal: python manage.py speaker_audit_listener --once)
        is_manage_py = any('manage.py' in str(arg).lower() for arg in sys.argv)
        is_runserver = any('runserver' in str(arg).lower() for arg in sys.argv)

        # Jika dipanggil via CLI manage.py selain runserver, jangan jalankan background thread otomatis
        if is_manage_py and not is_runserver:
            return

        # Jika runserver development, pastikan hanya jalan di child worker utama (RUN_MAIN == 'true')
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        # Monitoring 30-menit site verticality E32_VER_WEES dinonaktifkan.
        # Digantikan dengan background audit scheduler untuk perangkat testing (E32_IPS_7) tiap 30 menit.
        try:
            from .speaker_audit_monitor import start_speaker_audit_scheduler
            start_speaker_audit_scheduler()
        except Exception as e:
            print(f"[SPEAKER AUDIT SCHEDULER START ERROR] {e}", flush=True)
