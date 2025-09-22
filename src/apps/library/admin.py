from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from django.utils.html import format_html
from django.db.models import Q
from .models import * # Import all models


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'nationality', 'birth_date', 'biblio_count']
    list_filter = ['nationality', 'birth_date']
    search_fields = ['name', 'bio']
    readonly_fields = ['created_at', 'updated_at']
    
    def biblio_count(self, obj):
        return obj.biblios.count()
    biblio_count.short_description = "Biblios"


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'biblio_count']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def biblio_count(self, obj):
        return obj.biblio_set.count()
    biblio_count.short_description = "Biblios"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_genre']
    list_filter = ['parent_genre']
    search_fields = ['name', 'description']


class AuthorInline(GenericStackedInline):
    model = Author
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1
    fields = ['name', 'role']


class PublisherInline(GenericStackedInline):
    model = Publisher
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1
    fields = ['name', 'role', 'website']


class CoverInline(GenericStackedInline):
    model = Cover
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1
    fields = ['image_file', 'cover_type', 'is_primary', 'display_order', 'is_active']


class TaggedGenreInline(GenericStackedInline):
    model = TaggedGenre
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1


@admin.register(Biblio)
class BiblioAdmin(admin.ModelAdmin):
    list_display = ['title']
    list_filter = ['language']
    search_fields = ['title', 'isbn', 'issn', 'description']
    readonly_fields = ['created_at', 'updated_at', 'cover_preview']
    inlines = [TaggedGenreInline, AuthorInline, PublisherInline, CoverInline]
    
    def cover_preview(self, obj):
        if obj.cover_image_url:
            return format_html('<img src="{}" width="100" height="150" />', obj.cover_image_url)
        return "No cover"
    cover_preview.short_description = "Cover Preview"


@admin.register(TaggedGenre)
class TaggedGenreAdmin(admin.ModelAdmin):
    pass
