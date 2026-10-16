from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitoring'
    verbose_name = 'Structural Health Monitoring'

    def ready(self):
        import os
        from django.conf import settings
        if os.environ.get('RUN_MAIN') == 'true' or not settings.DEBUG:
            try:
                from .fatigue_monitor import start_fatigue_matrix_background_scheduler
                start_fatigue_matrix_background_scheduler()
            except Exception as e:
                print(f"[FATIGUE SCHEDULER START ERROR] {e}")
