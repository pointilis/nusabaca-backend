import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models
from .apps import LibraryConfig

app_label = LibraryConfig.label


class Author(models.Model):
    """
    Authors of books

    :name:
        The full name of the author. It must be unique. if two authors have the same name,
        consider adding middle names or initials to differentiate them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True)
    
    class Meta:
        db_table = f'{app_label}_authors'
        indexes = [
            GinIndex(fields=['search_vector']),
        ]
    
    def __str__(self):
        return self.name


class Publisher(models.Model):
    """
    Publishers of books

    :name:
        The name of the publisher. It should be unique to avoid confusion.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = f'{app_label}_publishers'
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Genre(models.Model):
    """Genres for books with hierarchical support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_genre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subgenres'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = f'{app_label}_genres'

    def __str__(self):
        return self.name


class Book(models.Model):
    """Central book entity - represents the work itself, not specific editions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, blank=True, help_text="Original title if translated")
    description = models.TextField(blank=True)
    original_publication_date = models.DateField(null=True, blank=True, help_text="First publication date of the work")
    language = models.CharField(max_length=10, default='en', help_text="Original language")
    authors = models.ManyToManyField(Author, through='BookAuthor', related_name='books')
    genres = models.ManyToManyField(Genre, through='BookGenre', related_name='books')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True)
    
    class Meta:
        db_table = f'{app_label}_books'
        indexes = [
            GinIndex(fields=['search_vector']),
            models.Index(fields=['original_publication_date']),
            models.Index(fields=['language']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def author_names(self):
        """Get comma-separated list of author names"""
        return ', '.join(self.authors.values_list('name', flat=True))
    
    @property
    def latest_edition(self):
        """Get the most recent edition of this book"""
        return self.editions.filter(is_available=True).order_by('-publication_date').first()
    
    @property
    def available_editions_count(self):
        """Count of available editions"""
        return self.editions.filter(is_available=True).count()


class BookEdition(models.Model):
    """Specific edition/version of a book"""
    
    FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('EPUB', 'EPUB'),
        ('MOBI', 'MOBI'),
        ('TXT', 'Text'),
        ('HTML', 'HTML'),
        ('AUDIOBOOK', 'Audiobook'),
        ('HARDCOVER', 'Hardcover'),
        ('PAPERBACK', 'Paperback'),
    ]
    
    EDITION_TYPE_CHOICES = [
        ('first', 'First Edition'),
        ('revised', 'Revised Edition'),
        ('reprint', 'Reprint'),
        ('anniversary', 'Anniversary Edition'),
        ('special', 'Special Edition'),
        ('international', 'International Edition'),
        ('translation', 'Translation'),
        ('abridged', 'Abridged Edition'),
        ('unabridged', 'Unabridged Edition'),
        ('illustrated', 'Illustrated Edition'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='editions')
    
    # Edition-specific metadata
    edition_title = models.CharField(max_length=500, blank=True, help_text="Edition-specific title if different")
    edition_number = models.CharField(max_length=50, blank=True, help_text="e.g., '2nd Edition', 'Revised'")
    edition_type = models.CharField(max_length=20, choices=EDITION_TYPE_CHOICES, default='other')
    isbn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    isbn13 = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # Publication details
    publishers = models.ManyToManyField(Publisher, through='BookPublisher', related_name='editions')
    publication_date = models.DateField(null=True, blank=True)
    edition_language = models.CharField(max_length=10, blank=True, help_text="Language of this edition")
    
    # Physical/Digital properties
    total_pages = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    file_path = models.CharField(max_length=1000, blank=True)
    file_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, blank=True)
    file_size_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cover_image_url = models.URLField(blank=True)
    
    # Edition-specific details
    translator = models.ManyToManyField(Author, blank=True, related_name='translated_editions')
    illustrator = models.ManyToManyField(Author, blank=True, related_name='illustrated_editions')
    editor = models.ManyToManyField(Author, blank=True, related_name='edited_editions')
    
    # Availability and metadata
    is_available = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False, help_text="Primary edition to display for this book")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Edition-specific notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = f'{app_label}_book_editions'
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['isbn']),
            models.Index(fields=['isbn13']),
            models.Index(fields=['publication_date']),
            models.Index(fields=['is_available'], condition=models.Q(is_available=True), name='available_editions_idx'),
            models.Index(fields=['is_primary'], condition=models.Q(is_primary=True), name='primary_editions_idx'),
            models.Index(fields=['edition_language']),
            models.Index(fields=['file_format']),
            models.Index(fields=['edition_type']),
        ]
        constraints = [
            # Only one primary edition per book
            models.UniqueConstraint(
                fields=['book'],
                condition=models.Q(is_primary=True),
                name='one_primary_edition_per_book'
            ),
        ]
    
    def __str__(self):
        edition_info = self.edition_number or self.get_edition_type_display()
        return f"{self.book.title} ({edition_info})"
    
    @property
    def display_title(self):
        """Get the title to display - edition-specific or main book title"""
        return self.edition_title or self.book.title
    
    @property
    def display_language(self):
        """Get the language to display - edition-specific or main book language"""
        return self.edition_language or self.book.language
    
    def save(self, *args, **kwargs):
        # If this is being set as primary, unset other primary editions for this book
        if self.is_primary:
            BookEdition.objects.filter(book=self.book, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        
        # If no primary edition exists for this book, make this one primary
        elif not BookEdition.objects.filter(book=self.book, is_primary=True).exclude(pk=self.pk).exists():
            self.is_primary = True
            
        super().save(*args, **kwargs)


class BookAuthor(models.Model):
    """Many-to-many relationship between books and authors with roles"""
    
    ROLE_CHOICES = [
        ('author', 'Author'),
        ('co-author', 'Co-Author'),
        ('editor', 'Editor'),
        ('translator', 'Translator'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='author')
    
    class Meta:
        db_table = f'{app_label}_book_authors'
        unique_together = ['book', 'author', 'role']
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['author']),
        ]


class BookGenre(models.Model):
    """Many-to-many relationship between books and genres"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        db_table = f'{app_label}_book_genres'
        unique_together = ['book', 'genre']
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['genre']),
        ]


class BookPublisher(models.Model):
    """Many-to-many relationship between books and publishers"""
    book_edition = models.ForeignKey(BookEdition, on_delete=models.CASCADE)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)

    class Meta:
        db_table = f'{app_label}_book_publishers'
        unique_together = ['book_edition', 'publisher']
        indexes = [
            models.Index(fields=['book_edition']),
            models.Index(fields=['publisher']),
        ]

