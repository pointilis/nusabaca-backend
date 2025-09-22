import os

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
from .apps import AudiobookConfig

app_label = AudiobookConfig.label


def audio_file_path(instance, filename):
    """Generate file path for audio files"""
    ext = filename.split('.')[-1]
    filename = f"chapter_{instance.chapter_number}.{ext}"
    return os.path.join('audiofiles', str(instance.audiobook.id), filename)


class Recognition(BaseModel):
    """OCR text recognition results for specific pages in biblios"""
    task_id = models.CharField(max_length=100, unique=True, help_text="Unique ID for the OCR processing task")
    biblio = models.ForeignKey('library.Biblio', on_delete=models.CASCADE, related_name='page_recognitions')
    page_number = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    full_text = models.TextField(help_text="The complete processed text content")
    language = models.CharField(max_length=10, default='en', help_text="Language code (e.g., 'en' for English)")
    result = models.JSONField(blank=True, null=True, help_text="Raw OCR results in JSON format")
    
    class Meta:
        db_table = f'{app_label}_page_recognitions'
        unique_together = ['biblio', 'page_number']
        indexes = [
            models.Index(fields=['biblio']),
            models.Index(fields=['page_number']),
            models.Index(fields=['created_by', 'biblio']),
        ]
    
    def __str__(self):
        return f"{self.biblio.title} p.{self.page_number} OCR"


class AudioFile(BaseModel):
    """Individual audio files/chapters within an audiobook"""
    recognition = models.ForeignKey(Recognition, on_delete=models.CASCADE, related_name='audio_files')

    # File Details
    audio_file = models.FileField(upload_to=audio_file_path)
    file_format = models.CharField(max_length=10)  # mp3, m4a, flac, etc.
    bitrate = models.PositiveIntegerField(null=True, blank=True)  # in kbps
    
    # Duration and Size
    duration_seconds = models.PositiveIntegerField()
    file_size_bytes = models.BigIntegerField()

    def __str__(self):
        return f"{self.recognition.biblio.title} - Page {self.recognition.page_number}"

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
        ordering = ['recognition', 'created_at']
        indexes = [
            models.Index(fields=['recognition']),
            models.Index(fields=['created_by']),
            models.Index(fields=['file_format']),
            models.Index(fields=['duration_seconds']),
            models.Index(fields=['file_size_bytes']),
            models.Index(fields=['created_at']),
            models.Index(fields=['recognition', 'created_at']),
            models.Index(fields=['created_by', 'recognition']),
        ]
