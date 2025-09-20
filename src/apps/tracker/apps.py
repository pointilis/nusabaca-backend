from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tracker'
    label = 'tracker'
    verbose_name = 'Tracker Application'

    def ready(self):
        from apps.tracker import signals  # noqa
        from apps.tracker import models  # noqa

        # Connect signals
        post_save.connect(signals.update_reading_progress_from_session,
                          sender=models.ReadingSession)
