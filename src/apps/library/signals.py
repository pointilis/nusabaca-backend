from apps.library.models import *
from django.contrib.postgres.search import SearchVector


def update_book_search_vector(sender, instance, **kwargs):
    """Update search vector for books"""
    Book.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('title', weight='A') + \
            SearchVector('description', weight='B')
    )


def update_book_edition_search_vector(sender, instance, **kwargs):
    """Update search vector for book editions"""
    Edition.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('edition_title', weight='A') + \
            SearchVector('isbn', 'isbn13', weight='B')
    )


def update_author_search_vector(sender, instance, **kwargs):
    """Update search vector for authors"""
    Author.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('name', 'bio', weight='A')
    )
