from django.apps import AppConfig


class AudiobookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audiobook'
    label = 'audiobook'
    verbose_name = 'Audiobook Application'

    def ready(self):
        import apps.audiobook.signals  # noqa
