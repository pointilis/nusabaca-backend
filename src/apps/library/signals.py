from apps.library.models import *
from django.contrib.postgres.search import SearchVector


def update_biblio_search_vector(sender, instance, **kwargs):
    """Update search vector for biblios"""
    try:
        Biblio.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('title', 'isbn', 'issn', weight='A') + \
                SearchVector('description', weight='B')
        )
    except Exception as e:
        # Handle exceptions
        pass


def update_author_search_vector(sender, instance, **kwargs):
    """Update search vector for authors"""
    try:
        Author.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('name', 'bio', weight='A')
        )
    except Exception as e:
        # Handle exceptions
        pass
