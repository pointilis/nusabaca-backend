from rest_framework import serializers
from apps.library.models import Biblio


class TTSSerializer(serializers.Serializer):
    """
    Serializer for text-to-speech processing requests.
    Validates text input and TTS parameters for background processing.
    """

    # Required text field (renamed from full_text to text for clarity)
    text = serializers.CharField(
        required=True,
        max_length=5000,  # Google TTS character limit
        help_text="Text to convert to speech (max 5000 characters)"
    )
    
    # TTS Processing options
    language = serializers.ChoiceField(
        choices=[
            ('id', 'Indonesian'),
            ('en', 'English (US)'),
            ('en-GB', 'English (UK)')
        ],
        default='en',
        required=False,
        help_text="Language for text-to-speech"
    )
    
    voice_gender = serializers.ChoiceField(
        choices=[
            ('male', 'Male'),
            ('female', 'Female')
        ],
        default='female',
        required=False,
        help_text="Voice gender preference"
    )
    
    voice_index = serializers.IntegerField(
        min_value=0,
        max_value=1,
        default=0,
        required=False,
        help_text="Voice index within gender category (0 or 1)"
    )
    
    audio_format = serializers.ChoiceField(
        choices=[
            ('mp3', 'MP3'),
            ('wav', 'WAV'),
            ('ogg', 'OGG Opus')
        ],
        default='mp3',
        required=False,
        help_text="Output audio format"
    )
    
    speaking_rate = serializers.FloatField(
        min_value=0.25,
        max_value=4.0,
        default=1.0,
        required=False,
        help_text="Speaking rate (0.25 to 4.0, 1.0 is normal)"
    )
    
    pitch = serializers.FloatField(
        min_value=-20.0,
        max_value=20.0,
        default=0.0,
        required=False,
        help_text="Pitch adjustment in semitones (-20.0 to 20.0)"
    )
    
    volume_gain_db = serializers.FloatField(
        min_value=-96.0,
        max_value=16.0,
        default=0.0,
        required=False,
        help_text="Volume gain in dB (-96.0 to 16.0)"
    )
    
    file_prefix = serializers.CharField(
        max_length=50,
        default='tts_audio',
        required=False,
        help_text="Prefix for generated audio filename"
    )
    
    # Optional metadata fields from Library app
    biblio = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        slug_field='id',
        queryset=Biblio.objects.all(),
        help_text="Associated bibliographic record"
    )
    
    page_number = serializers.IntegerField(
        required=False,
        help_text="Page number for bibliographic reference"
    )
    
    # Support legacy field name for backward compatibility
    full_text = serializers.CharField(
        required=False,
        max_length=5000,
        help_text="Legacy field name for text (use 'text' instead)"
    )
    
    def validate(self, data):
        """
        Validate the entire serializer data.
        """
        # Handle legacy full_text field
        if 'full_text' in data and not data.get('text'):
            data['text'] = data['full_text']
        
        # Ensure we have text content
        if not data.get('text'):
            raise serializers.ValidationError(
                {'text': 'Either text or full_text field is required'}
            )
        
        return data
    
    def validate_text(self, value):
        """
        Validate the text content.
        """
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Text cannot be empty")
        
        # Remove excessive whitespace
        cleaned_text = ' '.join(value.split())
        
        if len(cleaned_text) < 1:
            raise serializers.ValidationError("Text must contain at least 1 character")
        
        return cleaned_text
    
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
            'ar', 'hi', 'th', 'vi', 'nl', 'sv', 'da', 'no', 'fi', 'pl',
            'id', 'tr', 'el', 'he', 'ro', 'hu', 'cs', 'sk', 'uk', 'bg',
            'hr', 'lt', 'lv', 'et', 'sl', 'sr',
        ]
        
        if language and language.lower() not in supported_languages:
            raise serializers.ValidationError(
                f"Unsupported language code. Supported languages: {', '.join(supported_languages)}"
            )
        
        return language.lower() if language else 'en'
    
    def to_representation(self, instance):
        """
        Custom representation to include file information.
        """
        data = super().to_representation(instance)
        
        return data
