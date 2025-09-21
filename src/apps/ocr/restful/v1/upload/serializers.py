import os
import mimetypes
from rest_framework import serializers
from apps.library.models import Biblio


class FileSerializer(serializers.Serializer):
    """
    Serializer for file uploads, specifically designed for OCR processing.
    Validates image files and prepares them for text extraction.
    """
    
    # Fields coming from Library app
    biblio = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        slug_field='id',
        queryset=Biblio.objects.all()
    )
    page_number = serializers.IntegerField()

    # File to be uploaded (photo taken of the page)
    file = serializers.FileField(
        required=True,
        help_text="Image file to process for OCR (JPEG, PNG, GIF, BMP, WebP, TIFF)"
    )
    
    # Optional fields for additional processing options
    language = serializers.CharField(
        max_length=10,
        required=False,
        default='en',
        help_text="Language code for OCR processing (e.g., 'en', 'es', 'fr')"
    )
    
    extract_format = serializers.ChoiceField(
        choices=[
            ('text', 'Plain Text'),
            ('json', 'JSON with coordinates'),
            ('structured', 'Structured document format')
        ],
        default='text',
        required=False,
        help_text="Format for extracted text output"
    )
    
    confidence_threshold = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        default=0.8,
        required=False,
        help_text="Minimum confidence threshold for text detection (0.0 to 1.0)"
    )
    
    # Supported image file extensions and MIME types
    SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif']
    SUPPORTED_MIME_TYPES = [
        'image/jpeg',
        'image/png', 
        'image/gif',
        'image/bmp',
        'image/webp',
        'image/tiff'
    ]
    
    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    
    def validate_file(self, file):
        """
        Validate the uploaded file for OCR processing.
        
        Args:
            file: The uploaded file object
            
        Returns:
            file: The validated file object
            
        Raises:
            ValidationError: If the file doesn't meet the requirements
        """
        if not file:
            raise serializers.ValidationError("No file provided.")
        
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size too large. Maximum allowed size is {self.MAX_FILE_SIZE / (1024*1024):.1f}MB."
            )
        
        # Check file extension
        file_name = file.name.lower()
        file_extension = os.path.splitext(file_name)[1]
        
        if file_extension not in self.SUPPORTED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file format. Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise serializers.ValidationError(
                f"Invalid file type. Expected image file, got: {mime_type or 'unknown'}"
            )
        
        # Additional validation for file content (basic check)
        try:
            # Read a small portion to ensure it's not corrupted
            file.seek(0)
            header = file.read(1024)
            file.seek(0)  # Reset file pointer
            
            if not header:
                raise serializers.ValidationError("File appears to be empty or corrupted.")
                
        except Exception as e:
            raise serializers.ValidationError(f"Error reading file: {str(e)}")
        
        return file
    
    def validate_language(self, language):
        """
        Validate the language code.
        
        Args:
            language (str): Language code
            
        Returns:
            str: Validated language code
        """
        # Common language codes supported by Google Vision API
        supported_languages = [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
            'ar', 'hi', 'th', 'vi', 'nl', 'sv', 'da', 'no', 'fi', 'pl'
        ]
        
        if language and language.lower() not in supported_languages:
            raise serializers.ValidationError(
                f"Unsupported language code. Supported languages: {', '.join(supported_languages)}"
            )
        
        return language.lower() if language else 'en'
    
    def get_file_info(self):
        """
        Get information about the uploaded file.
        
        Returns:
            dict: File information including size, type, and name
        """
        if not self.validated_data.get('file'):
            return {}
        
        file = self.validated_data['file']
        mime_type, _ = mimetypes.guess_type(file.name)
        
        return {
            'name': file.name,
            'size': file.size,
            'size_mb': round(file.size / (1024 * 1024), 2),
            'mime_type': mime_type,
            'extension': os.path.splitext(file.name.lower())[1]
        }
    
    def to_representation(self, instance):
        """
        Custom representation to include file information.
        """
        data = super().to_representation(instance)
        
        if self.validated_data.get('file'):
            data['file_info'] = self.get_file_info()
        
        return data


class FileUploadResponseSerializer(serializers.Serializer):
    """
    Serializer for file upload response data.
    """
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    file_info = serializers.DictField(required=False)
    processing_id = serializers.CharField(required=False)
    
    # OCR results (when processing is complete)
    ocr_result = serializers.DictField(required=False)


class OCRResultSerializer(serializers.Serializer):
    """
    Serializer for OCR processing results.
    """
    
    processing_id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'), 
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ]
    )
    full_text = serializers.CharField(allow_blank=True)
    confidence = serializers.FloatField(required=False)
    text_blocks = serializers.ListField(required=False)
    pages = serializers.ListField(required=False)
    processing_time = serializers.FloatField(required=False)
    error_message = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(required=False)
    completed_at = serializers.DateTimeField(required=False)
