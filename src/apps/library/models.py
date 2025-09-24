from pathlib import Path
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db import models
from django.core.files.storage import default_storage
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase

from apps.core.models import BaseModel
from .apps import LibraryConfig

app_label = LibraryConfig.label


def cover_upload_path(instance, filename):
    """
    Generate upload path for cover images
    Format: covers/{content_type}/{object_id}/{cover_type}/{filename}
    """
    # Get the content type name (e.g., 'biblio')
    content_type_name = instance.content_type.model.lower()
    
    # Clean filename and preserve extension
    name, ext = Path(filename).stem, Path(filename).suffix
    clean_name = "".join(c for c in name if c.isalnum() or c in ('-', '_')).rstrip()
    clean_filename = f"{clean_name}{ext}".lower()
    
    return f"covers/{content_type_name}/{instance.object_id}/{instance.cover_type}/{clean_filename}"


class Author(BaseModel):
    """
    Authors of biblios

    :name:
        The full name of the author. It must be unique. if two authors have the same name,
        consider adding middle names or initials to differentiate them.
    """
    ROLE_CHOICES = [
        ('author', 'Author'),
        ('co-author', 'Co-Author'),
        ('editor', 'Editor'),
        ('translator', 'Translator'),
    ]

    name = models.CharField(max_length=255, unique=True)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='author')
    
    # Search vector for full-text search
    search_vector = SearchVectorField(null=True)

    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        db_table = f'{app_label}_authors'
        indexes = [
            GinIndex(fields=['search_vector']),
        ]
    
    def __str__(self):
        return self.name


class Publisher(BaseModel):
    """
    Publishers of biblios

    :name:
        The name of the publisher. It should be unique to avoid confusion.
    """
    ROLE_CHOICES = [
        ('publisher', 'Publisher'),
        ('co_publisher', 'Co-Publisher'),
        ('distributor', 'Distributor'),
        ('original_publisher', 'Original Publisher'),
        ('reprint_publisher', 'Reprint Publisher'),
    ]

    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    # Additional relationship metadata
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='publisher')
    publication_date = models.DateField(null=True, blank=True, help_text="Date this publisher released this content")
    notes = models.TextField(blank=True)

    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        db_table = f'{app_label}_publishers'
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class TaggedPublisher(GenericTaggedItemBase):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     limit_choices_to=(models.Q(app_label='library', model='biblio')))
    object_id = models.UUIDField()
    tag = models.ForeignKey(Publisher, on_delete=models.CASCADE,
                            related_name="%(app_label)s_%(class)s_items",
                            verbose_name="Publishers Tag")


class Genre(BaseModel):
    """Genres for biblios with hierarchical support"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_genre = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='sub_genres'
    )

    class Meta:
        db_table = f'{app_label}_genres'

    def __str__(self):
        return self.name


class TaggedGenre(GenericTaggedItemBase):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,
                                     limit_choices_to=(models.Q(app_label='library', model='biblio')))
    object_id = models.UUIDField()
    tag = models.ForeignKey(Genre, on_delete=models.CASCADE,
                            related_name="%(app_label)s_%(class)s_items",
                            verbose_name="Genres Tag")


class BiblioBaseModel(models.Model):
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

    title = models.CharField(max_length=500)
    isbn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    issn = models.CharField(max_length=20, unique=True, null=True, blank=True)
    original_title = models.CharField(max_length=500, blank=True, help_text="Original title if translated")
    description = models.TextField(blank=True)
    publication_year = models.PositiveIntegerField(null=True, blank=True, help_text="Year of publication")
    original_publication_date = models.DateField(null=True, blank=True, help_text="First publication date of the work")
    language = models.CharField(max_length=10, default='en', help_text="Original language")

    # Edition-specific metadata
    edition_title = models.CharField(max_length=500, blank=True, help_text="Edition-specific title if different")
    edition_number = models.CharField(max_length=50, blank=True, help_text="e.g., '2nd Edition', 'Revised'")
    edition_type = models.CharField(max_length=20, choices=EDITION_TYPE_CHOICES, default='other')

    # Physical/Digital properties
    total_pages = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    file_path = models.CharField(max_length=1000, blank=True)
    file_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, blank=True)
    file_size_mb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Explicit many-to-many relationship for genres using django-taggit
    genres = TaggableManager(through=TaggedGenre, verbose_name="Genres")

    # Explicit many-to-many relationship for publishers using django-taggit
    publishers = TaggableManager(through=TaggedPublisher, verbose_name="Publishers")

    # Generic relations
    covers = GenericRelation('library.Cover', related_query_name='biblio')
    authors = GenericRelation('library.Author', related_query_name='biblio')

    # Search vector for full-text search
    search_vector = SearchVectorField(null=True)

    class Meta:
        abstract = True


class Biblio(BaseModel, BiblioBaseModel):
    """Central biblio entity - represents the work itself"""

    class Meta:
        db_table = f'{app_label}_biblios'
        unique_together = [('title', 'isbn', 'issn')]
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
    def covers(self):
        """Get all covers for this biblio ordered by display_order"""
        return self.covers.filter(is_active=True).order_by('display_order', '-is_primary', '-quality_rating', '-created_at')

    @property
    def primary_cover(self):
        """Get the primary front cover for this biblio"""
        return self.covers.filter(cover_type='front', is_primary=True).first()
    
    @property
    def front_cover(self):
        """Get the best front cover for this biblio"""
        return self.covers.filter(cover_type='front').first() or self.primary_cover
    
    def add_cover(self, image_url=None, image_file=None, cover_type='front', title='', is_primary=False, display_order=None, **kwargs):
        """Add a cover to this biblio (supports both URL and file upload)"""
        if not image_url and not image_file:
            raise ValueError("Either image_url or image_file must be provided")
        
        if image_url and image_file:
            raise ValueError("Provide either image_url or image_file, not both")
        
        content_type = ContentType.objects.get_for_model(self)
        
        # Auto-assign display_order if not provided
        if display_order is None:
            display_order = Cover.get_next_display_order(content_type, self.id, cover_type)
        
        cover_data = {
            'content_type': content_type,
            'object_id': self.id,
            'cover_type': cover_type,
            'title': title or f"{self.title} - {cover_type.title()} Cover",
            'is_primary': is_primary,
            'display_order': display_order,
            **kwargs
        }
        
        if image_url:
            cover_data['image_url'] = image_url
        else:
            cover_data['image_file'] = image_file
            
        cover = Cover.objects.create(**cover_data)
        return cover
    
    def get_covers_by_type(self, cover_type='front'):
        """Get covers of a specific type ordered by display_order"""
        return self.covers.filter(cover_type=cover_type).order_by('display_order')


class Cover(BaseModel):
    """
    Cover images for biblios using content type framework
    Supports multiple cover types and formats
    """
    COVER_TYPE_CHOICES = [
        ('front', 'Front Cover'),
        ('back', 'Back Cover'),
        ('spine', 'Spine'),
        ('dust_jacket', 'Dust Jacket'),
        ('thumbnail', 'Thumbnail'),
        ('high_res', 'High Resolution'),
    ]
    
    FORMAT_CHOICES = [
        ('JPEG', 'JPEG'),
        ('PNG', 'PNG'),
        ('WEBP', 'WebP'),
        ('SVG', 'SVG'),
        ('GIF', 'GIF'),
    ]
    
    # Generic foreign key to any model (Biblio, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Cover metadata
    cover_type = models.CharField(max_length=20, choices=COVER_TYPE_CHOICES, default='front')
    title = models.CharField(max_length=255, help_text="Descriptive title for this cover")
    description = models.TextField(blank=True)
    
    # File information - support both upload and URL
    image_file = models.ImageField(
        upload_to=cover_upload_path,
        blank=True,
        null=True,
        help_text="Upload cover image file directly"
    )
    image_url = models.URLField(blank=True, help_text="URL to external cover image")
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, blank=True)
    file_size_kb = models.PositiveIntegerField(null=True, blank=True, help_text="File size in kilobytes")
    
    # Image dimensions
    width = models.PositiveIntegerField(null=True, blank=True, help_text="Image width in pixels")
    height = models.PositiveIntegerField(null=True, blank=True, help_text="Image height in pixels")
    
    # Additional metadata
    photographer = models.CharField(max_length=255, blank=True, help_text="Cover photographer/designer")
    copyright_info = models.TextField(blank=True, help_text="Copyright information")
    is_primary = models.BooleanField(default=False, help_text="Primary cover to display")
    is_active = models.BooleanField(default=True, help_text="Whether this cover is active/visible")
    
    # Quality and source information
    quality_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1)],
        help_text="Quality rating 1-5 (5 being highest)"
    )
    source = models.CharField(max_length=255, blank=True, help_text="Source of the cover image")
    
    # Display ordering
    display_order = models.PositiveIntegerField(
        default=1,
        help_text="Display order (1=first image, 2=second image, etc.)"
    )
    
    class Meta:
        db_table = f'{app_label}_covers'
        unique_together = ['content_type', 'object_id', 'cover_type', 'is_primary']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['cover_type']),
            models.Index(fields=['display_order']),
            models.Index(fields=['content_type', 'object_id', 'display_order']),
            models.Index(fields=['is_primary'], condition=models.Q(is_primary=True), name='primary_covers_idx'),
            models.Index(fields=['is_active'], condition=models.Q(is_active=True), name='active_covers_idx'),
            models.Index(fields=['file_format']),
            models.Index(fields=['quality_rating']),
        ]
        constraints = [
            # Only one primary cover per object per cover type
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'cover_type'],
                condition=models.Q(is_primary=True),
                name='one_primary_cover_per_type'
            ),
            # Unique display order per object and cover type
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'cover_type', 'display_order'],
                name='unique_display_order_per_cover_type'
            ),
        ]
    
    def __str__(self):
        return f"{self.content_object} - {self.get_cover_type_display()}"
    
    @property
    def image_source_url(self):
        """Get the actual URL to display the image (uploaded file or external URL)"""
        if self.image_file:
            return self.image_file.url
        return self.image_url or None
    
    @property
    def is_uploaded_file(self):
        """Check if this cover uses an uploaded file"""
        return bool(self.image_file)
    
    @property
    def is_external_url(self):
        """Check if this cover uses an external URL"""
        return bool(self.image_url and not self.image_file)
    
    @property
    def file_path(self):
        """Get the file path for uploaded files"""
        if self.image_file:
            return self.image_file.path
        return None
    
    @property
    def aspect_ratio(self):
        """Calculate aspect ratio if dimensions are available"""
        if self.width and self.height:
            return round(self.width / self.height, 2)
        return None
    
    @property
    def file_size_mb(self):
        """Convert file size to MB"""
        if self.file_size_kb:
            return round(self.file_size_kb / 1024, 2)
        return None
    
    def clean(self):
        """Custom validation to ensure either image_file or image_url is provided"""
        from django.core.exceptions import ValidationError
        
        if not self.image_file and not self.image_url:
            raise ValidationError("Either image_file or image_url must be provided.")
        
        if self.image_file and self.image_url:
            raise ValidationError("Provide either image_file or image_url, not both.")
    
    def get_file_info(self):
        """Extract file information from uploaded file"""
        if not self.image_file:
            return
        
        try:
            # Get file size
            self.file_size_kb = round(self.image_file.size / 1024)
            
            # Try to get image dimensions
            if hasattr(self.image_file, 'width') and hasattr(self.image_file, 'height'):
                self.width = self.image_file.width
                self.height = self.image_file.height
            
            # Detect file format from file extension
            if self.image_file.name:
                ext = Path(self.image_file.name).suffix.lower()
                format_mapping = {
                    '.jpg': 'JPEG',
                    '.jpeg': 'JPEG', 
                    '.png': 'PNG',
                    '.webp': 'WEBP',
                    '.svg': 'SVG',
                    '.gif': 'GIF'
                }
                self.file_format = format_mapping.get(ext, '')
                
        except Exception as e:
            # Log error but don't fail the save
            pass
    
    def save(self, *args, **kwargs):
        # Extract file information for uploaded files
        if self.image_file:
            self.get_file_info()
        
        # If this is being set as primary, unset other primary covers of the same type
        if self.is_primary:
            Cover.objects.filter(
                content_type=self.content_type,
                object_id=self.object_id,
                cover_type=self.cover_type,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        # If no primary cover exists for this type, make this one primary
        elif not Cover.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
            cover_type=self.cover_type,
            is_primary=True
        ).exclude(pk=self.pk).exists():
            self.is_primary = True
            
        super().save(*args, **kwargs)
    
    @classmethod
    def get_next_display_order(cls, content_type, object_id, cover_type):
        """Get the next available display order for a given object and cover type"""
        last_cover = cls.objects.filter(
            content_type=content_type,
            object_id=object_id,
            cover_type=cover_type
        ).order_by('-display_order').first()
        
        return (last_cover.display_order + 1) if last_cover else 1
    
    def move_to_position(self, new_position):
        """Move this cover to a specific display position"""
        if new_position < 1:
            new_position = 1
            
        # Get all covers of the same type for the same object
        covers = Cover.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id,
            cover_type=self.cover_type
        ).exclude(pk=self.pk).order_by('display_order')
        
        # Update positions
        position = 1
        for cover in covers:
            if position == new_position:
                position += 1
            cover.display_order = position
            cover.save(update_fields=['display_order'])
            position += 1
        
        # Set this cover's position
        self.display_order = new_position
        self.save(update_fields=['display_order'])
    
    def swap_positions(self, other_cover):
        """Swap display positions with another cover"""
        if (self.content_type != other_cover.content_type or 
            self.object_id != other_cover.object_id or
            self.cover_type != other_cover.cover_type):
            raise ValueError("Can only swap positions between covers of the same object and type")
        
        # Swap the positions
        self_order = self.display_order
        other_order = other_cover.display_order
        
        self.display_order = other_order
        other_cover.display_order = self_order
        
        self.save(update_fields=['display_order'])
        other_cover.save(update_fields=['display_order'])
    
    def delete(self, *args, **kwargs):
        """Delete the uploaded file when the cover is deleted"""
        if self.image_file:
            # Delete the file from storage
            default_storage.delete(self.image_file.name)
        super().delete(*args, **kwargs)

