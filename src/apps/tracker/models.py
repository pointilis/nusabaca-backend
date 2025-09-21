import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import F
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel
from .apps import TrackerConfig

app_label = TrackerConfig.label


class Collection(BaseModel):
    """User collections/libraries for organizing books"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    books = models.ManyToManyField('library.Book', through='CollectionBook', related_name='collections')

    class Meta:
        db_table = f'{app_label}_collections'
        unique_together = ['created_by', 'name']
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['created_by', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.created_by.username} - {self.name}"


class CollectionBook(BaseModel):
    """Books within user collections with personal metadata"""
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE)
    edition = models.ForeignKey('library.Edition', on_delete=models.CASCADE, null=True, blank=True, 
                                help_text="Specific edition in this collection")
    personal_rating = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    personal_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = f'{app_label}_collection_books'
        unique_together = ['collection', 'book', 'edition']
        indexes = [
            models.Index(fields=['collection']),
            models.Index(fields=['book']),
            models.Index(fields=['edition']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        # If no edition specified, use the primary edition
        if not self.edition and self.book:
            self.edition = self.book.editions.filter(is_primary=True).first()
        super().save(*args, **kwargs)


class ReadingSession(BaseModel):
    """Individual reading sessions for detailed tracking"""
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE, related_name='reading_sessions')
    edition = models.ForeignKey('library.Edition', on_delete=models.CASCADE, related_name='reading_sessions',
                                help_text="Specific edition being read")
    start_page = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    end_page = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    device_info = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = f'{app_label}_reading_sessions'
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['book']),
            models.Index(fields=['edition']),
            models.Index(fields=['start_time']),
            models.Index(fields=['created_by', 'book', 'start_time']),
            models.Index(fields=['created_by', 'edition', 'start_time']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_page__gte=F('start_page')),
                name='end_page_gte_start_page'
            ),
            models.CheckConstraint(
                check=models.Q(end_time__gte=F('start_time')) | models.Q(end_time__isnull=True),
                name='end_time_gte_start_time'
            ),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration if both times are present
        if self.start_time and self.end_time and not self.duration_minutes:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
            
        # If no edition specified, use the primary edition
        if not self.edition and self.book:
            self.edition = self.book.editions.filter(is_primary=True).first()
            
        super().save(*args, **kwargs)


class ReadingProgress(BaseModel):
    """Current reading state for each user-book-edition combination"""
    
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('reading', 'Reading'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('dropped', 'Dropped'),
    ]
    
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE, related_name='reading_progress')
    edition = models.ForeignKey('library.Edition', on_delete=models.CASCADE, related_name='reading_progress',
                                help_text="Specific edition being read")
    current_page = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    total_pages_read = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    reading_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_read_at = models.DateTimeField(default=timezone.now)
    estimated_time_remaining = models.PositiveIntegerField(null=True, blank=True)  # in minutes

    class Meta:
        db_table = f'{app_label}_reading_progress'
        unique_together = ['created_by', 'book', 'edition']
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['book']),
            models.Index(fields=['edition']),
            models.Index(fields=['created_by', 'book']),
            models.Index(fields=['created_by', 'edition']),
            models.Index(fields=['reading_status']),
            models.Index(fields=['last_read_at']),
            models.Index(fields=['progress_percentage']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(completed_at__gte=F('started_at')) | models.Q(completed_at__isnull=True),
                name='completed_at_gte_started_at'
            ),
        ]
    
    def save(self, *args, **kwargs):
        # If no edition specified, use the primary edition
        if not self.edition and self.book:
            self.edition = self.book.editions.filter(is_primary=True).first()
            
        # Auto-calculate progress percentage based on edition's total pages
        if self.edition and self.edition.total_pages > 0:
            self.progress_percentage = round(
                (self.total_pages_read / self.edition.total_pages) * 100, 2
            )
        
        # Auto-set completion status and timestamp
        if self.edition and self.current_page >= self.edition.total_pages and self.reading_status != 'completed':
            self.reading_status = 'completed'
            if not self.completed_at:
                self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        edition_info = f" ({self.edition.edition_number})" if self.edition.edition_number else ""
        return f"{self.created_by.username} - {self.book.title}{edition_info} ({self.progress_percentage}%)"


class Bookmark(BaseModel):
    """User bookmarks for specific pages in specific editions"""
    book = models.ForeignKey('library.Book', on_delete=models.CASCADE, related_name='bookmarks')
    edition = models.ForeignKey('library.Edition', on_delete=models.CASCADE, related_name='bookmarks',
                                help_text="Specific edition this bookmark refers to")
    page_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    title = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = f'{app_label}_bookmarks'
        unique_together = ['created_by', 'book', 'edition', 'page_number']
        indexes = [
            models.Index(fields=['created_by', 'book']),
            models.Index(fields=['created_by', 'edition']),
            models.Index(fields=['book', 'page_number']),
            models.Index(fields=['edition', 'page_number']),
        ]
    
    def save(self, *args, **kwargs):
        # If no edition specified, use the primary edition
        if not self.edition and self.book:
            self.edition = self.book.editions.filter(is_primary=True).first()
        super().save(*args, **kwargs)
    
    def __str__(self):
        edition_info = f" ({self.edition.edition_number})" if self.edition.edition_number else ""
        return f"{self.created_by.username} - {self.book.title}{edition_info} p.{self.page_number}"


class ReadingGoal(BaseModel):
    """User reading goals and targets"""
    
    GOAL_TYPE_CHOICES = [
        ('books_per_year', 'Books per Year'),
        ('pages_per_day', 'Pages per Day'),
        ('minutes_per_day', 'Minutes per Day'),
    ]

    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    target_value = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    current_value = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    year = models.PositiveIntegerField()

    class Meta:
        db_table = f'{app_label}_reading_goals'
        unique_together = ['created_by', 'goal_type', 'year']
    
    @property
    def progress_percentage(self):
        """Calculate goal progress percentage"""
        if self.target_value > 0:
            return min(round((self.current_value / self.target_value) * 100, 2), 100)
        return 0
    
    def __str__(self):
        return f"{self.created_by.username} - {self.get_goal_type_display()} {self.year}"


# Custom managers for common queries
class CurrentlyReadingManager(models.Manager):
    """Manager for currently reading books"""
    def get_queryset(self):
        return super().get_queryset().filter(reading_status='reading')


class CompletedBooksManager(models.Manager):
    """Manager for completed books"""
    def get_queryset(self):
        return super().get_queryset().filter(reading_status='completed')


# Add custom managers to ReadingProgress
ReadingProgress.add_to_class('currently_reading', CurrentlyReadingManager())
ReadingProgress.add_to_class('completed', CompletedBooksManager())
