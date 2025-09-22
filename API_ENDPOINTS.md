# API Endpoints Documentation

This document describes the available API endpoints for OCR and TTS processing.

## Base URL Structure
```
/api/ocr/v1/
```

## Available Endpoints

### 🧪 **Test Endpoints**
```
GET/POST /api/ocr/v1/test-task/
- Test endpoint for Celery task processing
- Used for debugging and health checks
```

---

### 📄 **OCR (Optical Character Recognition) Endpoints**

#### **Synchronous OCR**
```
POST /api/ocr/v1/upload/
- Synchronous file upload and OCR processing
- Returns results immediately (may take longer)
- Use for small files or when immediate results are needed
```

#### **Asynchronous OCR**
```
POST /api/ocr/v1/upload/async/
- Asynchronous file upload and OCR processing
- Returns task ID immediately, processes in background
- Recommended for larger files or batch processing

GET /api/ocr/v1/upload/status/{task_id}/
- Check status of asynchronous OCR task
- Returns progress, results when complete, or error details

GET /api/ocr/v1/upload/tasks/
- List recent OCR processing tasks
- Useful for task management and history
```

---

### 🎤 **TTS (Text-to-Speech) Endpoints**

#### **Asynchronous TTS**
```
POST /api/ocr/v1/tts/async/
- Submit text for speech synthesis
- Returns task ID immediately, processes in background
- Supports multiple languages, voices, and audio formats

GET /api/ocr/v1/tts/status/{task_id}/
- Check status of TTS processing task
- Returns progress, download URL when complete

GET /api/ocr/v1/tts/tasks/
- List recent TTS processing tasks
- Task history and management
```

---

## 🎤 **TTS API Usage Examples**

### **Submit TTS Task**
```bash
curl -X POST http://localhost:8000/api/ocr/v1/tts/async/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test message!",
    "language": "en",
    "voice_gender": "female",
    "audio_format": "mp3",
    "speaking_rate": 1.0,
    "pitch": 0.0,
    "volume_gain_db": 0.0
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "TTS request submitted successfully. Processing in background.",
  "task_id": "abc123-def456-ghi789",
  "status": "PENDING",
  "text_info": {
    "length": 28,
    "preview": "Hello, this is a test message!",
    "language": "en"
  },
  "processing_options": {
    "language_code": "en",
    "voice_gender": "female",
    "audio_format": "mp3",
    "speaking_rate": 1.0,
    "pitch": 0.0,
    "volume_gain_db": 0.0
  },
  "status_url": "http://localhost:8000/api/ocr/v1/tts/status/abc123-def456-ghi789/",
  "polling_instructions": {
    "check_url": "http://localhost:8000/api/ocr/v1/tts/status/abc123-def456-ghi789/",
    "recommended_interval_seconds": 3,
    "timeout_minutes": 10
  }
}
```

### **Check TTS Task Status**
```bash
curl http://localhost:8000/api/ocr/v1/tts/status/abc123-def456-ghi789/
```

**Response (In Progress):**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "processing",
  "progress": 50,
  "message": "Generating audio with en female voice",
  "updated_at": "2025-09-22T10:30:45Z",
  "polling_instructions": {
    "recommended_interval_seconds": 3,
    "timeout_minutes": 10
  }
}
```

**Response (Completed):**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "completed",
  "progress": 100,
  "message": "TTS generation completed successfully",
  "updated_at": "2025-09-22T10:31:15Z",
  "processing_id": "tts_task_abc123_1695384675000",
  "text_info": {
    "original_text": "Hello, this is a test message!",
    "text_length": 28,
    "language": "en",
    "voice_gender": "female",
    "voice_index": 0,
    "voice_name": "en-US-Chirp-A"
  },
  "audio_info": {
    "format": "mp3",
    "size": 15420,
    "size_mb": 0.01,
    "duration_estimate": 11.2,
    "speaking_rate": 1.0,
    "pitch": 0.0,
    "volume_gain_db": 0.0
  },
  "storage_info": {
    "storage_type": "google_cloud_storage",
    "upload_success": true,
    "file_path": "gs://bucket/tts_audio/en/filename.mp3",
    "filename": "tts_audio_en_en_US_Chirp_A_uuid.mp3",
    "gcs_blob_name": "tts_audio/en/filename.mp3",
    "bucket_name": "your-tts-bucket"
  },
  "download_url": "https://storage.googleapis.com/bucket/signed-url",
  "download_expires_at": "2025-09-23T10:31:15Z",
  "audio_file": {
    "filename": "tts_audio_en_en_US_Chirp_A_uuid.mp3",
    "format": "mp3",
    "size": 15420,
    "size_mb": 0.01,
    "duration_estimate": 11.2
  },
  "processing_completed_at": "2025-09-22T10:31:15Z"
}
```

---

## 🎛️ **TTS Parameters**

### **Required Parameters**
- `text` (string): Text to convert to speech (max 5000 characters)

### **Optional Parameters**
- `language` (string): Language code
  - `'en'` - English (US) [default]
  - `'id'` - Indonesian
  - `'en-GB'` - English (UK)

- `voice_gender` (string): Voice gender preference
  - `'female'` [default]
  - `'male'`

- `voice_index` (integer): Voice variation within gender (0-1)
  - `0` [default] - First voice
  - `1` - Second voice

- `audio_format` (string): Output audio format
  - `'mp3'` [default] - MP3 format
  - `'wav'` - WAV format  
  - `'ogg'` - OGG Opus format

- `speaking_rate` (float): Speaking speed (0.25 - 4.0)
  - `1.0` [default] - Normal speed
  - `0.5` - Half speed
  - `2.0` - Double speed

- `pitch` (float): Pitch adjustment in semitones (-20.0 to 20.0)
  - `0.0` [default] - Normal pitch
  - `-5.0` - Lower pitch
  - `+5.0` - Higher pitch

- `volume_gain_db` (float): Volume adjustment in dB (-96.0 to 16.0)
  - `0.0` [default] - Normal volume
  - `6.0` - Louder
  - `-6.0` - Quieter

- `file_prefix` (string): Custom filename prefix
  - `'tts_audio'` [default]

### **Metadata Parameters**
- `biblio` (uuid): Associated bibliographic record ID
- `page_number` (integer): Page number reference

---

## 🎵 **Available Voices**

### **Indonesian (id)**
- **Female**: id-ID-Chirp-A, id-ID-Chirp-C
- **Male**: id-ID-Chirp-B, id-ID-Chirp-D

### **English US (en)**
- **Female**: en-US-Chirp-A, en-US-Chirp-C
- **Male**: en-US-Chirp-B, en-US-Chirp-D

### **English UK (en-GB)**
- **Female**: en-GB-Chirp-A, en-GB-Chirp-C
- **Male**: en-GB-Chirp-B, en-GB-Chirp-D

---

## 📊 **Response Status Codes**

- `202 Accepted` - Task submitted successfully
- `200 OK` - Status check successful
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Task not found
- `500 Internal Server Error` - Server error

---

## 🔄 **Task Status Flow**

```
pending → processing → completed
    ↓         ↓
  failed ← retrying
```

- **pending**: Task queued, waiting to start
- **processing**: Task currently being processed
- **completed**: Task finished successfully
- **failed**: Task failed with errors
- **retrying**: Task failed but retrying automatically

---

## 💡 **Best Practices**

1. **Polling**: Check status every 3-5 seconds for TTS tasks
2. **Timeouts**: Set reasonable timeouts (10 minutes for TTS)
3. **Text Length**: Keep text under 5000 characters for best performance
4. **Download URLs**: Use download URLs promptly as they expire (24 hours)
5. **Error Handling**: Always check the `success` field in responses
6. **Rate Limiting**: Be mindful of API rate limits for production use

---

## 🛠️ **Development Setup**

1. **Django Server**: `python manage.py runserver`
2. **Celery Worker**: `celery -A nusabaca worker --loglevel=info`
3. **Redis Server**: Required for Celery task queue
4. **Google Cloud**: Configure credentials and storage buckets

---

## 📚 **Related Documentation**

- [GOOGLE_TTS.md](./GOOGLE_TTS.md) - Detailed TTS class documentation
- Django REST Framework documentation
- Google Cloud Text-to-Speech API documentation
- Celery documentation for background task processing