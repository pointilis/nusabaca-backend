from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.library'
    label = 'library'
    verbose_name = 'Library Application'

    def ready(self):
        from apps.library import signals  # noqa
        from apps.library import models  # noqa

        # Connect signals
        post_save.connect(signals.update_book_search_vector, sender=models.Book)
        post_save.connect(signals.update_book_search_vector, sender=models.BookEdition)
        post_save.connect(signals.update_author_search_vector, sender=models.Author)
