# Nusabaca - OCR & TTS Processing System

A comprehensive Django-based system for Optical Character Recognition (OCR) and Text-to-Speech (TTS) processing using Google Cloud services with asynchronous task processing.

## 🚀 Features

### 📄 OCR (Optical Character Recognition)
- **Google Cloud Vision API** integration
- **Synchronous and asynchronous** processing
- **File upload** support (images, PDFs)
- **Progress tracking** with task IDs
- **Background processing** with Celery

### 🎤 TTS (Text-to-Speech)
- **Google Cloud Text-to-Speech API** with Chirp voices
- **Multi-language support**: Indonesian, English (US/UK)
- **Voice customization**: Gender, pitch, speed, volume
- **Multiple audio formats**: MP3, WAV, OGG
- **Google Cloud Storage** integration
- **Asynchronous processing** with real-time status updates

### 📚 Library Management
- **Book and Edition** management
- **Author and Publisher** relationships
- **Cover management** with file uploads
- **Genre classification**
- **Abstract BaseModel** with UUID primary keys
- **Django REST Framework** APIs

## 🏗️ Architecture

### Core Technologies
- **Django 5.2.6** - Web framework
- **Django REST Framework 3.16.1** - API development
- **Celery 5.4.0** - Asynchronous task processing
- **Redis** - Task queue and caching
- **PostgreSQL** - Primary database
- **Google Cloud Services**:
  - Cloud Vision API (OCR)
  - Cloud Text-to-Speech API (TTS)
  - Cloud Storage (File storage)

### Project Structure
```
nusabaca/
├── src/
│   ├── manage.py
│   ├── core/                 # Django project settings
│   │   ├── settings/
│   │   ├── urls.py
│   │   └── wsgi.py
│   └── apps/
│       ├── ocr/              # OCR & TTS processing
│       │   ├── models.py
│       │   ├── views.py
│       │   ├── tasks.py      # Celery tasks
│       │   ├── lib/
│       │   │   └── google_vision.py
│       │   └── restful/      # API endpoints
│       │       └── v1/
│       └── library/          # Library management
│           ├── models.py     # Book, Author, etc.
│           └── api/
├── requirements.txt
├── service-account.json      # Google Cloud credentials
├── API_ENDPOINTS.md          # API documentation
└── GOOGLE_TTS.md            # TTS class documentation
```

## 🛠️ Installation & Setup

### 1. Prerequisites
- Python 3.9+
- Redis server
- PostgreSQL (recommended) or SQLite
- Google Cloud Platform account

### 2. Clone Repository
```bash
git clone <repository-url>
cd nusabaca
```

### 3. Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Google Cloud Setup
1. Create a Google Cloud Project
2. Enable APIs:
   - Cloud Vision API
   - Cloud Text-to-Speech API
   - Cloud Storage API
3. Create a service account and download JSON key
4. Place the key file as `service-account.json` in project root
5. Create Google Cloud Storage buckets for file storage

### 6. Environment Configuration
Update `src/core/settings/development.py`:
```python
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT = 'your-project-id'
GCS_BUCKET_NAME = 'your-bucket-name'
GCS_TTS_BUCKET = 'your-tts-bucket-name'
```

### 7. Database Setup
```bash
cd src
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 🚀 Running the System

### 1. Start Django Server
```bash
cd src
python manage.py runserver
```

### 2. Start Celery Worker
```bash
# In a separate terminal
cd src
celery -A core worker --loglevel=info
```

### 3. Start Redis Server
```bash
redis-server
```

### 4. Access the System
- **Django Admin**: http://localhost:8000/admin/
- **API Base URL**: http://localhost:8000/api/ocr/v1/
- **API Documentation**: See [API_ENDPOINTS.md](./API_ENDPOINTS.md)

## 📡 API Usage

### Quick Start Examples

#### **OCR Processing**
```bash
# Asynchronous OCR
curl -X POST http://localhost:8000/api/ocr/v1/upload/async/ \
  -F "file=@document.pdf"

# Check status
curl http://localhost:8000/api/ocr/v1/upload/status/{task_id}/
```

#### **TTS Processing**
```bash
# Generate speech
curl -X POST http://localhost:8000/api/ocr/v1/tts/async/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test!",
    "language": "en",
    "voice_gender": "female"
  }'

# Check status
curl http://localhost:8000/api/ocr/v1/tts/status/{task_id}/
```

## 🎛️ Configuration

### Key Settings
Located in `src/core/settings/base.py`:

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

# Google Cloud Storage
GOOGLE_CLOUD_PROJECT = 'your-project-id'
GCS_BUCKET_NAME = 'your-storage-bucket'
GCS_TTS_BUCKET = 'your-tts-bucket'

# File Upload Settings
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Available Languages & Voices

#### **Indonesian (id)**
- Female: id-ID-Chirp-A, id-ID-Chirp-C
- Male: id-ID-Chirp-B, id-ID-Chirp-D

#### **English US (en)**
- Female: en-US-Chirp-A, en-US-Chirp-C
- Male: en-US-Chirp-B, en-US-Chirp-D

#### **English UK (en-GB)**
- Female: en-GB-Chirp-A, en-GB-Chirp-C
- Male: en-GB-Chirp-B, en-GB-Chirp-D

## 🧪 Testing

### Run Tests
```bash
cd src
python manage.py test
```

### Test API Endpoints
```bash
# Test Celery connectivity
curl http://localhost:8000/api/ocr/v1/test-task/

# Test TTS functionality
curl -X POST http://localhost:8000/api/ocr/v1/tts/async/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message", "language": "en"}'
```

## 📊 Monitoring & Debugging

### Celery Monitoring
```bash
# View active tasks
celery -A core inspect active

# View worker statistics  
celery -A core inspect stats
```

### Django Logs
```bash
# Enable debug logging in settings
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

## 🔧 Troubleshooting

### Common Issues

#### **Google Cloud Authentication**
```bash
# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
```

#### **Celery Connection Issues**
- Ensure Redis is running
- Check Redis connection: `redis-cli ping`
- Verify Celery broker URL in settings

#### **File Upload Issues**
- Check `MEDIA_ROOT` permissions
- Verify Google Cloud Storage bucket permissions
- Ensure service account has Storage Object Admin role

## 📚 Documentation

- **[API_ENDPOINTS.md](./API_ENDPOINTS.md)** - Complete API documentation
- **[GOOGLE_TTS.md](./GOOGLE_TTS.md)** - TTS class documentation
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Google Cloud TTS**: https://cloud.google.com/text-to-speech/docs
- **Celery**: https://docs.celeryproject.org/

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

[Add your license information here]

## 👥 Support

For support and questions:
- Create an issue in the repository
- Check the documentation files
- Review the API endpoints documentation

---

**Version**: 1.0.0  
**Last Updated**: September 2025