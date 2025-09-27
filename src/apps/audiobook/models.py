import os

from datetime import datetime
from django.db import models
from django.core.validators import MinValueValidator
from storages.backends.gcloud import GoogleCloudStorage
from apps.core.models import BaseModel
from .apps import AudiobookConfig

app_label = AudiobookConfig.label


def audio_file_path(instance, filename):
    """Generate file path for audio files"""
    ext = filename.split('.')[-1]
    filename = f"page_{instance.page_number}.{ext}"
    return os.path.join('audiofiles', str(instance.id), filename)


def page_file_path(instance, filename):
    """Generate file path for page files"""
    file_extension = os.path.splitext(filename)[1].lower()
    clean_filename = os.path.splitext(filename)[0][:50]
    timestamp = datetime.now().strftime('%Y/%m/%d')
    biblio_collection_id = str(instance.biblio_collection.id) if instance.biblio_collection else 'unknown'

    uploaded_file_path = f"pages/{timestamp}/{biblio_collection_id}_{instance.page_number}_{clean_filename}{file_extension}"
    return uploaded_file_path


class AudioFileStorage(GoogleCloudStorage):
    """Custom storage for audio files in Google Cloud Storage"""
    bucket_name = os.getenv('GOOGLE_CLOUD_TTS_BUCKET', 'nusabaca_tts_bucket')


class PageFileStorage(GoogleCloudStorage):
    """Custom storage for page files in Google Cloud Storage"""
    bucket_name = os.getenv('GOOGLE_CLOUD_PAGE_BUCKET', 'nusabaca_page_bucket')
    

class PageFile(BaseModel):
    """OCR text recognition results for specific pages in biblios"""
    task_id = models.CharField(max_length=100, unique=True, null=True, help_text="Unique ID for the OCR processing task")
    biblio_collection = models.ForeignKey('tracker.BiblioCollection', on_delete=models.CASCADE, related_name='page_files')
    
    page_file = models.FileField(upload_to=page_file_path, storage=PageFileStorage, 
                                 max_length=500, help_text="Uploaded image file of the page")
    file_format = models.CharField(max_length=10)  # pdf, jpg, png, etc.
    page_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    full_text = models.TextField(help_text="The complete processed text content")
    language = models.CharField(max_length=10, default='en', help_text="Language code (e.g., 'en' for English)")
    voice_gender = models.CharField(max_length=10, default='male', help_text="Voice gender for TTS (e.g., 'male', 'female')")
    result = models.JSONField(blank=True, null=True, help_text="Raw OCR results in JSON format")
    
    class Meta:
        db_table = f'{app_label}_page_files'
        unique_together = ['biblio_collection', 'page_number']
        indexes = [
            models.Index(fields=['biblio_collection']),
            models.Index(fields=['page_number']),
            models.Index(fields=['created_by', 'biblio_collection']),
        ]
    
    def __str__(self):
        return f"{self.biblio_collection.title} p.{self.page_number} OCR"

    def save(self, *args, **kwargs):
        # Auto-detect file format if not set
        if not self.file_format and self.page_file:
            self.file_format = os.path.splitext(self.page_file.name)[1][1:].lower()
        super().save(*args, **kwargs)


class AudioFile(BaseModel):
    """Individual audio files/chapters within an audiobook"""
    task_id = models.CharField(max_length=100, unique=True, null=True, help_text="Unique ID for the OCR processing task")
    biblio_collection = models.ForeignKey('tracker.BiblioCollection', on_delete=models.CASCADE, related_name='audiofiles')
    page_file = models.OneToOneField(PageFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='audiofile')

    # File Details
    language = models.CharField(max_length=10, default='en', help_text="Language code (e.g., 'en' for English)")
    voice_gender = models.CharField(max_length=10, default='male', help_text="Voice gender for TTS (e.g., 'male', 'female')")
    page_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    audio_file = models.FileField(upload_to=audio_file_path, storage=AudioFileStorage, 
                                  max_length=500, help_text="Generated audio file for the page")
    file_format = models.CharField(max_length=10)  # mp3, m4a, flac, etc.
    bitrate = models.PositiveIntegerField(null=True, blank=True)  # in kbps
    
    # Duration and Size
    duration_seconds = models.PositiveIntegerField()
    file_size_bytes = models.BigIntegerField()
    result = models.JSONField(blank=True, null=True, help_text="Raw TTS results in JSON format")

    def __str__(self):
        return f"{self.biblio_collection.title} - Page {self.page_number}"

    def save(self, *args, **kwargs):
        # Auto-detect file format if not set
        if not self.file_format and self.audio_file:
            self.file_format = os.path.splitext(self.audio_file.name)[1][1:].lower()
        super().save(*args, **kwargs)

    @property
    def file_size_mb(self):
        return round(self.file_size_bytes / (1024 * 1024), 2)

    @property
    def duration_formatted(self):
        """Return duration in MM:SS format"""
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    class Meta:
        db_table = f'{app_label}_audio_files'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['biblio_collection']),
            models.Index(fields=['created_by']),
            models.Index(fields=['file_format']),
            models.Index(fields=['duration_seconds']),
            models.Index(fields=['file_size_bytes']),
            models.Index(fields=['created_at']),
            models.Index(fields=['biblio_collection', 'created_at']),
            models.Index(fields=['created_by', 'biblio_collection']),
        ]
