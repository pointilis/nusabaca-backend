from django.contrib import admin
from .models import * #noqa


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    pass


@admin.register(BiblioCollection)
class BiblioCollectionAdmin(admin.ModelAdmin):
    list_display = ('biblio', 'collection', 'personal_rating')
