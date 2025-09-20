from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tracker'
    label = 'tracker'
    verbose_name = 'Tracker Application'
