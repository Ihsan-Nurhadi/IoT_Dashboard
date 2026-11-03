from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Structural Health Monitoring'

    def ready(self):
        import os
        from django.conf import settings
        if os.environ.get('RUN_MAIN') == 'true' or not settings.DEBUG:
            # Monitoring 30-menit site verticality E32_VER_WEES dinonaktifkan.
            # Digantikan dengan background audit scheduler untuk perangkat testing (E32_IPS_7) tiap 30 menit.
            try:
                from .speaker_audit_monitor import start_speaker_audit_scheduler
                start_speaker_audit_scheduler()
            except Exception as e:
                print(f"[SPEAKER AUDIT SCHEDULER START ERROR] {e}")
