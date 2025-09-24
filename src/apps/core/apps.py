from django.apps import AppConfig
from django.db.models.signals import post_save


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'
    verbose_name = 'Core Application'

    def ready(self):
        import apps.core.signals  # noqa
        from django.contrib.auth.models import User

        # User saved signal
        post_save.connect(apps.core.signals.user_saved, sender=User, dispatch_uid='user_saved')
