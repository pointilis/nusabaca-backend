from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from django.db.models import Q
from apps.library.models import * # Import all models


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ['name', 'nationality', 'birth_date', 'book_count']
    list_filter = ['nationality', 'birth_date']
    search_fields = ['name', 'bio']
    readonly_fields = ['created_at', 'updated_at']
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = "Books"


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ['name', 'website', 'book_count']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def book_count(self, obj):
        return obj.book_set.count()
    book_count.short_description = "Books"


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_genre', 'book_count']
    list_filter = ['parent_genre']
    search_fields = ['name', 'description']
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = "Books"


class BookAuthorInline(admin.TabularInline):
    model = BookAuthor
    extra = 1


class BookGenreInline(admin.TabularInline):
    model = BookGenre
    extra = 1


class PublisherInline(GenericTabularInline):
    model = PublisherRelation
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1


class CoverInline(GenericTabularInline):
    model = Cover
    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 1
    fields = ['image_file', 'cover_type', 'is_primary', 'display_order', 'is_active']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author_list']
    list_filter = ['language']
    search_fields = ['title', 'isbn', 'isbn13', 'description']
    readonly_fields = ['created_at', 'updated_at', 'cover_preview']
    inlines = [BookAuthorInline, BookGenreInline, PublisherInline, CoverInline]

    def author_list(self, obj):
        return obj.author_names
    author_list.short_description = "Authors"
    
    def cover_preview(self, obj):
        if obj.cover_image_url:
            return format_html('<img src="{}" width="100" height="150" />', obj.cover_image_url)
        return "No cover"
    cover_preview.short_description = "Cover Preview"


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    inlines = [PublisherInline, CoverInline]
