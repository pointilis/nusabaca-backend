# Google Text-to-Speech Integration

A comprehensive Django integration for Google Cloud Text-to-Speech API with Chirp voice support and Google Cloud Storage integration.

## Features

- 🎯 **Chirp Voice Support**: High-quality neural voices for Indonesian and English
- 🌐 **Multi-language**: Indonesian (`id`), English US (`en`), and English UK (`en-GB`)
- 📁 **Cloud Storage**: Automatic upload to Google Cloud Storage with organized file structure
- 🔒 **Security**: Private file storage with signed URLs for secure access
- 🎛️ **Advanced Controls**: Speaking rate, pitch, volume, and SSML support
- 📊 **File Management**: List, delete, and get info about generated audio files

## Installation

1. Install required dependencies:
```bash
pip install google-cloud-texttospeech google-cloud-storage
```

2. Set up Google Cloud credentials:
   - Create a service account in Google Cloud Console
   - Download the JSON key file
   - Set the environment variable or Django setting

## Configuration

Add these settings to your Django `settings.py`:

```python
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS = '/path/to/your/service-account-key.json'

# Google Cloud Storage bucket for TTS audio files
GOOGLE_CLOUD_TTS_BUCKET = 'your-tts-bucket-name'
```

### Environment Variables

Alternatively, you can use environment variables:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

## Basic Usage

### Quick Text-to-Speech

```python
from apps.ocr.lib.google_tts import quick_tts

# Simple text synthesis
result = quick_tts(
    text="Hello, this is a test message.",
    language='en',
    gender='female'
)

print(f"Audio saved to: {result['file_url']}")
```

### Using the Main Class

```python
from apps.ocr.lib.google_tts import GoogleTextToSpeech

# Initialize the TTS client
tts = GoogleTextToSpeech()

# Synthesize text
result = tts.synthesize_text(
    text="Selamat datang di aplikasi kami!",
    language_code='id',
    voice_gender='female',
    voice_index=0,
    audio_format='mp3'
)

print(f"Generated audio: {result['filename']}")
print(f"File size: {result['file_size']} bytes")
print(f"Download URL: {result['file_url']}")
```

## Advanced Usage

### Custom Voice Selection

```python
# Use specific voice settings
result = tts.synthesize_text(
    text="This is a professional announcement.",
    language_code='en',
    voice_gender='male',
    voice_index=1,  # Use second male voice
    speaking_rate=0.9,  # Slightly slower
    pitch=-2.0,  # Lower pitch
    volume_gain_db=2.0,  # Slightly louder
    audio_format='wav'
)
```

### SSML Support

```python
# Create SSML markup
ssml_content = tts.create_ssml(
    text="Welcome to our application!",
    language_code='en',
    speaking_rate=1.2,
    pitch='+1st',
    volume='loud',
    emphasis='moderate'
)

# Synthesize SSML
result = tts.synthesize_ssml(
    ssml=ssml_content,
    language_code='en',
    voice_gender='female'
)
```

### Custom SSML

```python
# Advanced SSML with breaks and emphasis
ssml = '''
<speak version="1.0" xml:lang="en-US">
    <prosody rate="medium" pitch="+2st">
        Welcome to our <emphasis level="strong">premium</emphasis> service!
    </prosody>
    <break time="1s"/>
    <prosody rate="slow">
        Please listen carefully to the following instructions.
    </prosody>
</speak>
'''

result = tts.synthesize_ssml(ssml=ssml)
```

## File Management

### List Audio Files

```python
from apps.ocr.lib.google_tts import manage_tts_audio

# List all TTS audio files
files = manage_tts_audio('list')
print(f"Found {files['count']} audio files")

# Filter by language
english_files = manage_tts_audio('list', language_code='en')

# Filter by voice
female_files = manage_tts_audio('list', voice_name='female')
```

### Get File Information

```python
# Get detailed info about a specific file
file_info = manage_tts_audio(
    'info', 
    gcs_blob_name='tts_audio/en/tts_audio_en_en_US_Chirp_A_uuid.mp3'
)

if file_info['success']:
    print(f"File size: {file_info['size']}")
    print(f"Created: {file_info['created']}")
    print(f"Download URL: {file_info['download_url']}")
```

### Delete Audio Files

```python
# Delete a specific file
result = manage_tts_audio(
    'delete', 
    gcs_blob_name='tts_audio/en/old_audio_file.mp3'
)

if result['success']:
    print("File deleted successfully")
```

## Available Voices

### Indonesian Voices
- **Female**: `id-ID-Chirp-A`, `id-ID-Chirp-C`
- **Male**: `id-ID-Chirp-B`, `id-ID-Chirp-D`

### English (US) Voices
- **Female**: `en-US-Chirp-A`, `en-US-Chirp-C`
- **Male**: `en-US-Chirp-B`, `en-US-Chirp-D`

### English (UK) Voices
- **Female**: `en-GB-Chirp-A`, `en-GB-Chirp-C`
- **Male**: `en-GB-Chirp-B`, `en-GB-Chirp-D`

### Get Available Voices

```python
# Get all available voices
voices = tts.get_available_voices()

# Get voices for specific language
indonesian_voices = tts.get_available_voices('id')
print(f"Indonesian voices: {indonesian_voices}")
```

## Audio Formats

Supported audio formats:
- **MP3**: `'mp3'` (default) - Good compression, widely supported
- **WAV**: `'wav'` - Uncompressed, high quality
- **OGG**: `'ogg'` - Open source format with good compression

## Parameters Reference

### synthesize_text Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Text to synthesize (required) |
| `language_code` | str | `'en'` | Language code: `'id'`, `'en'`, `'en-GB'` |
| `voice_gender` | str | `'female'` | Voice gender: `'male'` or `'female'` |
| `voice_index` | int | `0` | Voice index within gender (0-1) |
| `audio_format` | str | `'mp3'` | Audio format: `'mp3'`, `'wav'`, `'ogg'` |
| `speaking_rate` | float | `1.0` | Speaking rate (0.25 to 4.0) |
| `pitch` | float | `0.0` | Pitch adjustment (-20.0 to 20.0 semitones) |
| `volume_gain_db` | float | `0.0` | Volume gain (-96.0 to 16.0 dB) |
| `save_to_file` | bool | `True` | Whether to save audio to storage |
| `file_prefix` | str | `'tts_audio'` | Prefix for generated filename |

## File Storage Structure

Files are organized in Google Cloud Storage as follows:
```
your-bucket/
└── tts_audio/
    ├── id/          # Indonesian audio files
    │   ├── tts_audio_id_id_ID_Chirp_A_uuid1.mp3
    │   └── tts_audio_id_id_ID_Chirp_B_uuid2.wav
    ├── en/          # English (US) audio files
    │   ├── tts_audio_en_en_US_Chirp_A_uuid3.mp3
    │   └── tts_audio_en_en_US_Chirp_C_uuid4.ogg
    └── en-GB/       # English (UK) audio files
        ├── tts_audio_en_GB_en_GB_Chirp_A_uuid5.mp3
        └── tts_audio_en_GB_en_GB_Chirp_B_uuid6.wav
```

## Response Format

### Successful Synthesis Response

```python
{
    'audio_content': b'...',  # Raw audio bytes
    'text': 'Hello world',
    'voice_name': 'en-US-Chirp-A',
    'language_code': 'en',
    'audio_format': 'mp3',
    'speaking_rate': 1.0,
    'pitch': 0.0,
    'volume_gain_db': 0.0,
    'content_length': 15420,
    
    # File storage information (if save_to_file=True)
    'file_path': 'gs://bucket/tts_audio/en/filename.mp3',
    'file_url': 'https://storage.googleapis.com/...',  # Signed URL
    'gcs_blob_name': 'tts_audio/en/filename.mp3',
    'filename': 'tts_audio_en_en_US_Chirp_A_uuid.mp3',
    'file_size': 15420,
    'storage_type': 'google_cloud_storage',
    'bucket_name': 'your-bucket',
    'upload_success': True,
    'signed_url_expires_at': '2025-09-23T12:00:00Z'
}
```

## Error Handling

```python
try:
    result = tts.synthesize_text("Hello world")
    if result['upload_success']:
        print(f"Success: {result['file_url']}")
    else:
        print("Synthesis succeeded but file upload failed")
except Exception as e:
    print(f"Error: {e}")
```

## Security Notes

- Audio files are stored privately in Google Cloud Storage
- Access is provided through signed URLs with configurable expiration (default: 24 hours)
- Service account credentials should be kept secure
- Use environment variables or Django settings for sensitive configuration

## Performance Tips

- The class initializes settings once during instantiation for better performance
- Reuse the same `GoogleTextToSpeech` instance for multiple synthesis operations
- Consider using shorter expiration times for signed URLs to enhance security
- Use appropriate audio formats: MP3 for web, WAV for high quality, OGG for open source projects

## Troubleshooting

### Common Issues

1. **Authentication Error**: Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account key
2. **Bucket Not Found**: Verify `GOOGLE_CLOUD_TTS_BUCKET` exists and is accessible
3. **Permission Denied**: Service account needs Storage Object Admin permissions
4. **Voice Not Available**: Check available voices using `get_available_voices()`

### Fallback Storage

If Google Cloud Storage is not configured or fails, the system automatically falls back to Django's default storage system.

## Integration Examples

### Django View Integration

```python
from django.http import JsonResponse
from apps.ocr.lib.google_tts import GoogleTextToSpeech

def generate_audio(request):
    text = request.POST.get('text')
    language = request.POST.get('language', 'en')
    
    tts = GoogleTextToSpeech()
    try:
        result = tts.synthesize_text(
            text=text,
            language_code=language,
            voice_gender='female'
        )
        
        return JsonResponse({
            'success': True,
            'audio_url': result['file_url'],
            'filename': result['filename'],
            'expires_at': result['signed_url_expires_at']
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

### Celery Task Integration

```python
from celery import shared_task
from apps.ocr.lib.google_tts import GoogleTextToSpeech

@shared_task
def generate_audio_async(text, language='en', voice_gender='female'):
    tts = GoogleTextToSpeech()
    result = tts.synthesize_text(
        text=text,
        language_code=language,
        voice_gender=voice_gender
    )
    
    return {
        'file_url': result['file_url'],
        'filename': result['filename'],
        'file_size': result['file_size']
    }
```

## License

This integration is part of the Nusabaca project and follows the project's licensing terms.