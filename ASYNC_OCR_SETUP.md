# Asynchronous OCR Processing with Django Celery

This system provides background processing for OCR tasks using Django, Celery, and Google Cloud services. Users get immediate responses while file processing happens in the background.

## 🚀 **Setup Instructions**

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Install and Start Redis**
```bash
# Windows (using Chocolatey)
choco install redis-64

# Or download from: https://github.com/microsoftarchive/redis/releases
# Start Redis server
redis-server

# Test Redis connection
redis-cli ping
```

### 3. **Environment Variables**
Create `.env` file with:
```env
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django Settings
DJANGO_SETTINGS_MODULE=nusabaca.settings.development
```

### 4. **Start Services**

**Terminal 1: Django Server**
```bash
cd src
python manage.py runserver
```

**Terminal 2: Celery Worker**
```bash
cd src
celery -A nusabaca worker --loglevel=info -E --queues=ocr_processing,tts_processing,status_check -P gevent (for windows use -P gevent)
```

**Terminal 3: Celery Monitor (Optional)**
```bash
cd src
celery -A nusabaca flower
# Visit: http://localhost:5555
```

## 🔧 **API Endpoints**

### **1. Async Upload** 
`POST /api/v1/upload/async/`

Submit file for background processing:

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/upload/async/ \
  -F "file=@document.jpg" \
  -F "language=en" \
  -F "extract_format=json" \
  -F "confidence_threshold=0.8"
```

**Response (202 Accepted):**
```json
{
  "success": true,
  "message": "File uploaded successfully. Processing in background.",
  "task_id": "abc123-def456-ghi789",
  "status": "PENDING",
  "file_info": {
    "name": "document.jpg",
    "size": 245760,
    "content_type": "image/jpeg"
  },
  "processing_options": {
    "language": "en",
    "extract_format": "json",
    "confidence_threshold": 0.8
  },
  "status_url": "http://localhost:8000/api/v1/upload/status/abc123-def456-ghi789/",
  "polling_instructions": {
    "check_url": "http://localhost:8000/api/v1/upload/status/abc123-def456-ghi789/",
    "recommended_interval_seconds": 5,
    "timeout_minutes": 30
  }
}
```

### **2. Check Task Status**
`GET /api/v1/upload/status/{task_id}/`

**Response (Processing):**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "processing",
  "progress": 60,
  "message": "Processing OCR with format: json",
  "updated_at": "2025-09-20T10:30:15Z",
  "polling_instructions": {
    "recommended_interval_seconds": 5,
    "timeout_minutes": 30
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
  "message": "OCR processing completed successfully",
  "processing_id": "task_abc123_1726833015123",
  "file_info": {
    "original_name": "document.jpg",
    "size": 245760,
    "content_type": "image/jpeg"
  },
  "storage_info": {
    "original_file": {
      "gcs_path": "uploads/2025/09/20/task_abc123_document.jpg",
      "gs_url": "gs://your-bucket/uploads/2025/09/20/task_abc123_document.jpg",
      "signed_url": "https://storage.googleapis.com/...",
      "signed_url_expires_at": "2025-09-20T11:30:15Z"
    },
    "results_file": {
      "gcs_path": "results/2025/09/20/task_abc123_results.json",
      "signed_url": "https://storage.googleapis.com/..."
    }
  },
  "ocr_result": {
    "full_text": "Extracted text content...",
    "processing_time": 2.45,
    "language": "en",
    "format": "json",
    "text_blocks_count": 15,
    "text_blocks": [
      {
        "text": "Sample text",
        "bounding_box": [[10, 20], [100, 20], [100, 40], [10, 40]],
        "confidence": 0.95
      }
    ]
  },
  "download_urls": {
    "original_file": "https://storage.googleapis.com/...",
    "results_file": "https://storage.googleapis.com/..."
  },
  "processing_completed_at": "2025-09-20T10:32:30Z"
}
```

### **3. List Tasks**
`GET /api/v1/upload/tasks/`

Lists recent tasks (not yet implemented).

## 📊 **Task Processing Pipeline**

```
1. File Upload (20%) → Upload to Google Cloud Storage
2. OCR Processing (40%) → Google Vision API text extraction  
3. Results Storage (70%) → Store results in GCS as JSON
4. URL Generation (90%) → Create signed URLs for downloads
5. Complete (100%) → Return comprehensive results
```

## 🔄 **Frontend Integration**

### **JavaScript Example:**

```javascript
class OCRProcessor {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
    }
    
    async uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', options.language || 'en');
        formData.append('extract_format', options.format || 'text');
        formData.append('confidence_threshold', options.confidence || 0.8);
        
        const response = await fetch(`${this.baseUrl}/api/v1/upload/async/`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    async checkStatus(taskId) {
        const response = await fetch(`${this.baseUrl}/api/v1/upload/status/${taskId}/`);
        return await response.json();
    }
    
    async processWithPolling(file, options = {}, onProgress = null) {
        // Upload file
        const uploadResult = await this.uploadFile(file, options);
        if (!uploadResult.success) {
            throw new Error(uploadResult.message);
        }
        
        const taskId = uploadResult.task_id;
        
        // Poll for completion
        return new Promise((resolve, reject) => {
            const pollInterval = setInterval(async () => {
                try {
                    const status = await this.checkStatus(taskId);
                    
                    if (onProgress) {
                        onProgress(status);
                    }
                    
                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        resolve(status);
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        reject(new Error(status.message));
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    reject(error);
                }
            }, 5000); // Check every 5 seconds
            
            // Timeout after 30 minutes
            setTimeout(() => {
                clearInterval(pollInterval);
                reject(new Error('Processing timeout'));
            }, 30 * 60 * 1000);
        });
    }
}

// Usage
const ocrProcessor = new OCRProcessor('http://localhost:8000');

document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const file = document.getElementById('file-input').files[0];
    const progressDiv = document.getElementById('progress');
    
    try {
        const result = await ocrProcessor.processWithPolling(
            file,
            { language: 'en', format: 'json' },
            (status) => {
                progressDiv.innerHTML = `
                    <p>Status: ${status.status}</p>
                    <p>Progress: ${status.progress}%</p>
                    <p>Message: ${status.message}</p>
                `;
            }
        );
        
        // Processing completed
        document.getElementById('results').innerHTML = `
            <h3>Extracted Text:</h3>
            <p>${result.ocr_result.full_text}</p>
            <p>Processing time: ${result.ocr_result.processing_time}s</p>
        `;
        
    } catch (error) {
        console.error('OCR processing failed:', error);
        progressDiv.innerHTML = `<p>Error: ${error.message}</p>`;
    }
});
```

## 🛠️ **Monitoring & Management**

### **Celery Monitoring:**
- **Flower UI**: `http://localhost:5555` - Web interface for monitoring tasks
- **Celery CLI**: `celery -A nusabaca inspect active` - View active tasks
- **Redis CLI**: `redis-cli monitor` - Monitor Redis operations

### **Task Management:**
```python
# In Django shell
from apps.ocr.tasks import get_ocr_task_status
from celery.result import AsyncResult

# Check task status
task_id = "your-task-id"
result = AsyncResult(task_id)
print(f"Status: {result.status}")
print(f"Result: {result.result}")

# Revoke task
result.revoke(terminate=True)
```

## 🔒 **Security & Performance**

### **Security Features:**
- File validation and size limits
- Signed URLs for temporary access
- User metadata tracking
- Input sanitization

### **Performance Optimizations:**
- Background processing prevents UI blocking
- Redis for fast task status retrieval  
- Google Cloud Storage for scalable file handling
- Celery for distributed task processing
- Progress tracking for user feedback

### **Production Considerations:**
- Use separate Redis instances for different environments
- Configure Celery workers on multiple servers
- Set up monitoring and alerting
- Implement task result cleanup
- Use SSL/TLS for production APIs

This asynchronous OCR system provides a professional, scalable solution for processing images in the background while maintaining excellent user experience! 🚀