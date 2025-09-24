from django.apps import AppConfig
from django.db.models.signals import post_save


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tracker'
    label = 'tracker'
    verbose_name = 'Tracker Application'

    def ready(self):
        from apps.tracker import signals  # noqa
        from apps.tracker import models  # noqa
        from apps.library import models as library_models  # noqa

        # Connect signals
        post_save.connect(signals.update_reading_progress_from_session,
                          sender=models.ReadingSession, dispatch_uid='reading_session_save')
        
        # Connect signal to add new biblios to default collection
        # post_save.connect(signals.insert_biblio_from_library_to_collection,
        #                   sender=library_models.Biblio, dispatch_uid='biblio_create')

        # Connect signal biblio collection save handler
        post_save.connect(signals.biblio_collection_save_handler,
                          sender=models.BiblioCollection, dispatch_uid='biblio_collection_save')
