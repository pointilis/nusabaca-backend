import os
import logging
import json
import requests

from typing import Dict, Any, Optional
from datetime import datetime
from celery import shared_task, current_task
from celery.exceptions import Retry
from django.conf import settings
from django.core.cache import cache

from apps.ocr.lib.google_vision import GoogleCloudVision
from apps.ocr.lib.google_storage import GoogleCloudStorage
from apps.ocr.lib.google_tts import GoogleTextToSpeech
from apps.ocr.lib.google_tts_stream import GoogleTTSStreaming

# Configure logger
logger = logging.getLogger(__name__)


class OCRTaskProcessor:
    """
    Class to handle OCR processing tasks with Google Cloud services.
    Manages file uploads to Google Storage and text recognition in background.
    """
    
    def __init__(self):
        # Store configuration variables
        self.bucket_name = getattr(settings, 'GOOGLE_CLOUD_PAGE_BUCKET', os.getenv('GOOGLE_CLOUD_PAGE_BUCKET'))
        self.service_account_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', 
                                          os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        self.project_id = getattr(settings, 'GOOGLE_CLOUD_PROJECT_ID', os.getenv('GOOGLE_CLOUD_PROJECT_ID'))
        self.gemini_api_key = os.getenv('GOOGLE_GENAI_API_KEY', None)
        
        # Initialize client placeholders
        self.storage_client = None
        self.vision_client = None
        
        # Initialize clients with stored config
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud clients using stored configuration."""
        try:
            # Initialize Google Cloud Storage
            if self.bucket_name:
                self.storage_client = GoogleCloudStorage(
                    bucket_name=self.bucket_name,
                    service_account_path=self.service_account_path,
                    project_id=self.project_id
                )
                logger.info(f"Google Cloud Storage client initialized in task processor for bucket: {self.bucket_name}")
            else:
                logger.warning("GCS bucket name not configured. Storage features will be disabled.")
            
            # Initialize Google Cloud Vision
            self.vision_client = GoogleCloudVision(self.service_account_path, self.gemini_api_key)
            
            if self.vision_client.is_client_ready():
                logger.info("Google Cloud Vision client initialized in task processor")
            else:
                logger.error("Google Cloud Vision client initialization failed in task processor")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud clients in task processor: {str(e)}")
    
    def is_ready(self) -> bool:
        """Check if both clients are ready."""
        storage_ready = self.storage_client and self.storage_client.is_client_ready()
        vision_ready = self.vision_client and self.vision_client.is_client_ready()
        return storage_ready and vision_ready
    
    def update_task_status(self, task_id: str, status: str, progress: int = 0, 
                          message: str = '', result: Optional[Dict] = None):
        """Update task status in cache for real-time progress tracking."""
        try:
            status_data = {
                'task_id': task_id,
                'status': status,
                'progress': progress,
                'message': message,
                'modified_at': datetime.now().isoformat(),
                'result': result or {}
            }
            
            # Store in cache with 1 hour expiration
            cache_key = f"ocr_task_{task_id}"
            cache.set(cache_key, status_data, timeout=3600)
            
            # Also update Celery task state
            if current_task:
                current_task.update_state(
                    state=status.upper(),
                    meta={
                        'progress': progress,
                        'message': message,
                        'current': progress,
                        'total': 100,
                        'result': result
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to update task status: {str(e)}")


class TTSTaskProcessor:
    """
    Class to handle Text-to-Speech processing tasks with Google Cloud services.
    Manages TTS audio generation and uploads to Google Cloud Storage.
    """
    
    def __init__(self):
        # Store configuration variables
        self.tts_bucket_name = getattr(settings, 'GOOGLE_CLOUD_TTS_BUCKET', None)
        self.service_account_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', 
                                          os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        
        # Initialize client placeholders
        self.tts_client = None
        
        # Initialize clients with stored config
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud TTS client using stored configuration."""
        try:
            # Initialize Google Text-to-Speech
            self.tts_client = GoogleTextToSpeech(self.service_account_path)
            logger.info("Google Text-to-Speech client initialized in task processor")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google TTS client in task processor: {str(e)}")
    
    def is_ready(self) -> bool:
        """Check if TTS client is ready."""
        return self.tts_client and self.tts_client.client is not None
    
    def update_task_status(self, task_id: str, status: str, progress: int = 0, 
                          message: str = '', result: Optional[Dict] = None):
        """Update task status in cache for real-time progress tracking."""
        try:
            status_data = {
                'task_id': task_id,
                'status': status,
                'progress': progress,
                'message': message,
                'modified_at': datetime.now().isoformat(),
                'result': result or {}
            }
            
            # Store in cache with 1 hour expiration
            cache_key = f"tts_task_{task_id}"
            cache.set(cache_key, status_data, timeout=3600)
            
            # Also update Celery task state
            if current_task:
                current_task.update_state(
                    state=status.upper(),
                    meta={
                        'progress': progress,
                        'message': message,
                        'current': progress,
                        'total': 100,
                        'result': result
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to update TTS task status: {str(e)}")


class TTSStreamingTaskProcessor:
    """
    Class to handle TTS Streaming processing tasks with Google Cloud services.
    Manages streaming TTS audio generation and uploads to Google Cloud Storage.
    """
    
    def __init__(self):
        # Store configuration variables
        self.service_account_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', 
                                          os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        
        # Initialize client placeholders
        self.tts_streaming_client = None
        
        # Initialize clients with stored config
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Google Cloud TTS Streaming client using stored configuration."""
        try:
            # Initialize Google Text-to-Speech Streaming
            self.tts_streaming_client = GoogleTTSStreaming(self.service_account_path)
            logger.info("Google Text-to-Speech Streaming client initialized in task processor")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google TTS Streaming client in task processor: {str(e)}")
    
    def is_ready(self) -> bool:
        """Check if TTS Streaming client is ready."""
        return self.tts_streaming_client and self.tts_streaming_client.tts_client is not None
    
    def update_task_status(self, task_id: str, status: str, progress: int = 0, 
                          message: str = '', result: Optional[Dict] = None):
        """Update task status in cache for real-time progress tracking."""
        try:
            status_data = {
                'task_id': task_id,
                'status': status,
                'progress': progress,
                'message': message,
                'modified_at': datetime.now().isoformat(),
                'result': result or {}
            }
            
            # Store in cache with 1 hour expiration
            cache_key = f"tts_streaming_task_{task_id}"
            cache.set(cache_key, status_data, timeout=3600)
            
            # Also update Celery task state
            if current_task:
                current_task.update_state(
                    state=status.upper(),
                    meta={
                        'progress': progress,
                        'message': message,
                        'current': progress,
                        'total': 100,
                        'result': result,
                        'synthesis_method': 'streaming'
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to update TTS Streaming task status: {str(e)}")


# Global task processor instances
ocr_task_processor = OCRTaskProcessor()
tts_task_processor = TTSTaskProcessor()
tts_streaming_task_processor = TTSStreamingTaskProcessor()


@shared_task(bind=True, ignore_result=False, max_retries=3, default_retry_delay=60)
def process_ocr_upload(self, file_data: bytes, filename: str, content_type: str,
                      language: str = 'en', extract_format: str = 'text',
                      confidence_threshold: float = 0.8,
                      voice_gender: str = 'male',
                      user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Background task to process file upload to Google Storage and perform OCR.
    
    Args:
        file_data (bytes): Binary file data
        filename (str): Original filename
        content_type (str): MIME content type
        language (str): Language code for OCR
        extract_format (str): Output format (text, json, structured)
        confidence_threshold (float): Minimum confidence for text detection
        user_metadata (dict): Additional metadata from user
        
    Returns:
        Dict[str, Any]: Processing results
    """
    task_id = self.request.id
    request_id = f"task_{task_id}_{int(datetime.now().timestamp() * 1000)}"
    
    logger.info(f"[{request_id}] Starting background OCR processing task: {task_id}")
    
    try:
        # Initialize progress tracking
        ocr_task_processor.update_task_status(
            task_id, 'PROCESSING', 0, 
            'Initializing OCR processing...'
        )
        
        # Check if task processor is ready
        if not ocr_task_processor.is_ready():
            error_msg = "Google Cloud services not available"
            logger.error(f"[{request_id}] {error_msg}")
            
            ocr_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'retry_count': self.request.retries}
            )
            
            # Retry if not at max retries
            if self.request.retries < self.max_retries:
                logger.info(f"[{request_id}] Retrying in {self.default_retry_delay} seconds")
                raise self.retry(countdown=self.default_retry_delay)
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id
            }
        
        # Generate file paths
        biblio_collection = user_metadata.get('biblio_collection', {}) if user_metadata else {}
        cid = biblio_collection.get('id', None)
        page_number = biblio_collection.get('page_number', 1)
        timestamp = datetime.now().strftime('%Y/%m/%d')
        file_extension = os.path.splitext(filename)[1].lower()
        clean_filename = os.path.splitext(filename)[0][:50]
        blob_path = f"pages/{timestamp}/{cid}_{page_number}_{clean_filename}{file_extension}"

        # Step 1: Upload file to Google Cloud Storage (20% progress)
        ocr_task_processor.update_task_status(
            task_id, 'PROCESSING', 20,
            f'Uploading file to Google Cloud Storage: {filename}'
        )
        
        upload_metadata = {
            'request_id': request_id,
            'task_id': task_id,
            'original_filename': filename,
            'upload_timestamp': datetime.now().isoformat(),
            'language': language,
            'extract_format': extract_format,
            'confidence_threshold': str(confidence_threshold)
        }
        
        # Add user metadata if provided
        if user_metadata:
            upload_metadata.update({f'user_{k}': str(v) for k, v in user_metadata.items()})
        
        storage_upload_result = ocr_task_processor.storage_client.upload_from_memory(
            file_data=file_data,
            destination_blob_name=blob_path,
            content_type=content_type,
            metadata=upload_metadata
        )
        
        if not storage_upload_result['success']:
            error_msg = f"Failed to upload file to storage: {storage_upload_result['message']}"
            logger.error(f"[{request_id}] {error_msg}")
            
            ocr_task_processor.update_task_status(
                task_id, 'FAILURE', 20, error_msg,
                {'error': error_msg, 'storage_result': storage_upload_result}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'storage_info': storage_upload_result,
                'user_metadata': user_metadata or {}
            }
        
        logger.info(f"[{request_id}] File uploaded successfully: {blob_path}")
        
        # Step 2: Process OCR (40% progress)
        ocr_task_processor.update_task_status(
            task_id, 'PROCESSING', 40,
            f'Processing OCR with format: {extract_format}'
        )
        
        ocr_start_time = datetime.now()
        
        # Perform OCR based on format
        if extract_format == 'structured':
            logger.info(f"[{request_id}] Starting structured document OCR processing")
            ocr_result = ocr_task_processor.vision_client.detect_document_text(file_data)
        else:
            logger.info(f"[{request_id}] Starting standard text OCR processing")
            ocr_result = ocr_task_processor.vision_client.detect_text(file_data)
        
        ocr_processing_time = (datetime.now() - ocr_start_time).total_seconds()
        
        if not ocr_result['success']:
            error_msg = f"OCR processing failed: {ocr_result['message']}"
            logger.error(f"[{request_id}] {error_msg}")
            
            ocr_task_processor.update_task_status(
                task_id, 'FAILURE', 40, error_msg,
                {
                    'error': error_msg,
                    'ocr_result': ocr_result,
                    'storage_info': storage_upload_result
                }
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'ocr_result': ocr_result,
                'storage_info': storage_upload_result,
                'voice_gender': voice_gender,
                'user_metadata': user_metadata or {}
            }
        
        logger.info(f"[{request_id}] OCR processing completed successfully in {ocr_processing_time:.2f}s")
        
        # Step 3: Store results (70% progress)
        ocr_task_processor.update_task_status(
            task_id, 'PROCESSING', 70,
            'Storing OCR results to Google Cloud Storage'
        )

        # Step 4: Generate signed URLs (90% progress)
        ocr_task_processor.update_task_status(
            task_id, 'PROCESSING', 90,
            'Generating secure access URLs'
        )
        
        # Generate signed URLs for temporary access
        signed_url_result = None

        try:
            # Original file signed URL (1 hour)
            signed_url_result = ocr_task_processor.storage_client.generate_signed_url(
                blob_path, expiration_minutes=60
            )
                
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to generate signed URLs: {str(e)}")
        
        # Step 5: Prepare final response (100% progress)
        final_result = {
            'success': True,
            'message': 'File processed successfully through background OCR pipeline',
            'task_id': task_id,
            'processing_id': request_id,
            'file_info': {
                'original_name': filename,
                'size': len(file_data),
                'size_mb': round(len(file_data) / (1024 * 1024), 2),
                'content_type': content_type
            },
            'storage_info': {
                'gcs_path': blob_path,
                'gs_url': storage_upload_result['gs_url'],
                'signed_url': signed_url_result['signed_url'] if signed_url_result and signed_url_result['success'] else None,
                'signed_url_expires_at': signed_url_result['expires_at'] if signed_url_result and signed_url_result['success'] else None
            },
            'ocr_result': {
                'full_text': ocr_result.get('full_text', ''),
                'confidence': confidence_threshold,
                'processing_time': round(ocr_processing_time, 2),
                'language': language,
                'voice_gender': voice_gender,
                'format': extract_format,
                'text_blocks_count': len(ocr_result.get('text_blocks', [])) if extract_format == 'json' else None,
                'pages_count': len(ocr_result.get('pages', [])) if extract_format == 'structured' else None
            },
            'processing_completed_at': datetime.now().isoformat(),
            'user_metadata': user_metadata or {}
        }
        
        # Add format-specific data
        if extract_format == 'json' and 'text_blocks' in ocr_result:
            final_result['ocr_result']['text_blocks'] = ocr_result['text_blocks']
        elif extract_format == 'structured' and 'pages' in ocr_result:
            final_result['ocr_result']['pages'] = ocr_result['pages']
        
        # Update final status
        ocr_task_processor.update_task_status(
            task_id, 'SUCCESS', 100,
            'OCR processing completed successfully',
            final_result
        )
        
        logger.info(f"[{request_id}] Background OCR task completed successfully")
        
        return final_result
        
    except Retry:
        # Re-raise retry exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error in background OCR task: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        
        ocr_task_processor.update_task_status(
            task_id, 'FAILURE', 0, error_msg,
            {
                'error': error_msg,
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries
            }
        )
        
        return {
            'success': False,
            'message': error_msg,
            'task_id': task_id,
            'processing_id': request_id,
            'error_details': {
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries
            },
            'user_metadata': user_metadata or {}
        }


@shared_task(bind=True, ignore_result=False, max_retries=3, default_retry_delay=60)
def process_tts_generation(self, text: str, language_code: str = 'en',
                         voice_gender: str = 'female', voice_index: int = 0,
                         audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                         pitch: float = 0.0, volume_gain_db: float = 0.0,
                         file_prefix: str = 'tts_audio',
                         user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Background task to generate text-to-speech audio and upload to Google Cloud Storage.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category (0-1)
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        file_prefix (str): Prefix for generated filename
        user_metadata (dict): Additional metadata from user
        
    Returns:
        Dict[str, Any]: Processing results
    """
    task_id = self.request.id
    request_id = f"tts_task_{task_id}_{int(datetime.now().timestamp() * 1000)}"
    
    logger.info(f"[{request_id}] Starting background TTS generation task: {task_id}")
    
    try:
        # Initialize progress tracking
        tts_task_processor.update_task_status(
            task_id, 'PROCESSING', 0, 
            'Initializing TTS processing...'
        )
        
        # Check if task processor is ready
        if not tts_task_processor.is_ready():
            error_msg = "Google Text-to-Speech service not available"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'retry_count': self.request.retries}
            )
            
            # Retry if not at max retries
            if self.request.retries < self.max_retries:
                logger.info(f"[{request_id}] Retrying in {self.default_retry_delay} seconds")
                raise self.retry(countdown=self.default_retry_delay)
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id
            }
        
        # Validate text input
        if not text or len(text.strip()) == 0:
            error_msg = "Text input is required and cannot be empty"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'text_length': len(text) if text else 0}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'user_metadata': user_metadata or {}
            }
        
        # Check text length limits (Google TTS has limits)
        text_length = len(text)
        if text_length > 5000:  # Google TTS limit is typically 5000 characters
            error_msg = f"Text too long: {text_length} characters (max 5000)"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'text_length': text_length}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'text_length': text_length,
                'user_metadata': user_metadata or {}
            }
        
        # Step 1: Generate TTS audio (50% progress)
        tts_task_processor.update_task_status(
            task_id, 'PROCESSING', 50,
            f'Generating audio with {language_code} {voice_gender} voice'
        )
        
        tts_start_time = datetime.now()
        
        try:
            tts_result = tts_task_processor.tts_client.synthesize_text(
                text=text,
                language_code=language_code,
                voice_gender=voice_gender,
                voice_index=voice_index,
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db,
                save_to_file=True,
                file_prefix=file_prefix,
                user_metadata=user_metadata
            )
            
            tts_processing_time = (datetime.now() - tts_start_time).total_seconds()
            
            if not tts_result.get('upload_success', False):
                error_msg = "TTS audio generation succeeded but file upload failed"
                logger.warning(f"[{request_id}] {error_msg}")
                
                # Still continue as we have the audio content
                tts_result['upload_success'] = False
                tts_result['storage_type'] = 'memory_only'
            
        except Exception as e:
            error_msg = f"TTS generation failed: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_task_processor.update_task_status(
                task_id, 'FAILURE', 50, error_msg,
                {
                    'error': error_msg,
                    'exception_type': type(e).__name__,
                    'text_length': text_length
                }
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'text_length': text_length,
                'user_metadata': user_metadata or {}
            }
        
        logger.info(f"[{request_id}] TTS generation completed successfully in {tts_processing_time:.2f}s")
        
        # Step 2: Prepare metadata and results (80% progress)
        tts_task_processor.update_task_status(
            task_id, 'PROCESSING', 80,
            'Preparing TTS results and metadata'
        )
        
        # Prepare comprehensive results
        final_result = {
            'success': True,
            'message': 'Text-to-speech generation completed successfully',
            'task_id': task_id,
            'processing_id': request_id,
            'text_info': {
                'original_text': text,
                'text_length': text_length,
                'language': language_code,
                'voice_gender': voice_gender,
                'voice_index': voice_index,
                'voice_name': tts_result.get('voice_name', 'unknown')
            },
            'audio_info': {
                'format': audio_encoding,
                'size': tts_result.get('file_size', tts_result.get('content_length', 0)),
                'size_mb': round(tts_result.get('file_size', tts_result.get('content_length', 0)) / (1024 * 1024), 2),
                'duration_estimate': round(text_length / 150 * 60, 1),  # Rough estimate: ~150 chars per minute
                'speaking_rate': speaking_rate,
                'pitch': pitch,
                'volume_gain_db': volume_gain_db
            },
            'storage_info': tts_result.get('storage_info', {}),
            'processing_info': {
                'processing_time': round(tts_processing_time, 2),
                'processed_at': datetime.now().isoformat(),
                'task_started_at': self.request.eta.isoformat() if self.request.eta else None,
                'file_prefix': file_prefix
            },
            'user_metadata': user_metadata or {}
        }
        
        # Step 3: Finalize (100% progress)
        tts_task_processor.update_task_status(
            task_id, 'SUCCESS', 100,
            'TTS generation completed successfully',
            final_result
        )
        
        logger.info(f"[{request_id}] Background TTS task completed successfully")
        
        return final_result
        
    except Retry:
        # Re-raise retry exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error in background TTS task: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        
        tts_task_processor.update_task_status(
            task_id, 'FAILURE', 0, error_msg,
            {
                'error': error_msg,
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries
            }
        )
        
        return {
            'success': False,
            'message': error_msg,
            'task_id': task_id,
            'processing_id': request_id,
            'error_details': {
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries
            },
            'user_metadata': user_metadata or {}
        }


@shared_task
def get_ocr_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of an OCR processing task.
    
    Args:
        task_id (str): Celery task ID
        
    Returns:
        Dict[str, Any]: Task status information
    """
    try:
        # First check cache for real-time status updates
        cache_key = f"ocr_task_{task_id}"
        status_data = cache.get(cache_key)
        
        if status_data:
            return status_data
        
        # Fallback to django-celery-results database
        try:
            from django_celery_results.models import TaskResult
            
            task_result = TaskResult.objects.filter(task_id=task_id).first()
            if task_result:
                # Parse result data
                result_data = {}
                if task_result.result:
                    try:
                        if isinstance(task_result.result, str):
                            result_data = json.loads(task_result.result)
                        else:
                            result_data = task_result.result
                    except (json.JSONDecodeError, TypeError):
                        result_data = {'raw_result': str(task_result.result)}
                
                return {
                    'task_id': task_id,
                    'status': task_result.status,
                    'progress': result_data.get('progress', 0) if isinstance(result_data, dict) else 0,
                    'message': result_data.get('message', '') if isinstance(result_data, dict) else '',
                    'result': result_data if isinstance(result_data, dict) else {},
                    'modified_at': task_result.date_done.isoformat() if task_result.date_done else task_result.date_created.isoformat(),
                    'created_at': task_result.date_created.isoformat(),
                    'task_name': task_result.task_name or 'unknown',
                    'worker': task_result.worker or 'unknown'
                }
        except ImportError:
            logger.warning("django_celery_results not available, falling back to AsyncResult")
        except Exception as e:
            logger.error(f"Error querying django_celery_results: {str(e)}")
        
        # Final fallback to Celery task state
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'progress': result.info.get('progress', 0) if result.info else 0,
            'message': result.info.get('message', '') if result.info else '',
            'result': result.info.get('result', {}) if result.info else {},
            'modified_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'progress': 0,
            'message': f'Failed to retrieve task status: {str(e)}',
            'result': {},
            'modified_at': datetime.now().isoformat()
        }


@shared_task
def get_tts_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of a TTS processing task.
    
    Args:
        task_id (str): Celery task ID
        
    Returns:
        Dict[str, Any]: Task status information
    """
    try:
        # First check cache for real-time status updates
        cache_key = f"tts_task_{task_id}"
        status_data = cache.get(cache_key)
        
        if status_data:
            return status_data
        
        # Fallback to django-celery-results database
        try:
            from django_celery_results.models import TaskResult
            
            task_result = TaskResult.objects.filter(task_id=task_id).first()
            if task_result:
                # Parse result data
                result_data = {}
                if task_result.result:
                    try:
                        if isinstance(task_result.result, str):
                            result_data = json.loads(task_result.result)
                        else:
                            result_data = task_result.result
                    except (json.JSONDecodeError, TypeError):
                        result_data = {'raw_result': str(task_result.result)}
                
                return {
                    'task_id': task_id,
                    'status': task_result.status,
                    'progress': result_data.get('progress', 0) if isinstance(result_data, dict) else 0,
                    'message': result_data.get('message', '') if isinstance(result_data, dict) else '',
                    'result': result_data if isinstance(result_data, dict) else {},
                    'modified_at': task_result.date_done.isoformat() if task_result.date_done else task_result.date_created.isoformat(),
                    'created_at': task_result.date_created.isoformat(),
                    'task_name': task_result.task_name or 'unknown',
                    'worker': task_result.worker or 'unknown'
                }
        except ImportError:
            logger.warning("django_celery_results not available, falling back to AsyncResult")
        except Exception as e:
            logger.error(f"Error querying django_celery_results: {str(e)}")
        
        # Final fallback to Celery task state
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'progress': result.info.get('progress', 0) if result.info else 0,
            'message': result.info.get('message', '') if result.info else '',
            'result': result.info.get('result', {}) if result.info else {},
            'modified_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get TTS task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'progress': 0,
            'message': f'Failed to retrieve task status: {str(e)}',
            'result': {},
            'modified_at': datetime.now().isoformat()
        }


@shared_task
def cleanup_old_task_statuses():
    """
    Background task to clean up old task status entries from cache.
    Should be run periodically (e.g., daily).
    """
    try:
        # This would require implementing a way to list cache keys
        # For now, we rely on cache TTL (1 hour) to handle cleanup
        logger.info("Task status cleanup completed (handled by cache TTL)")
        return {'success': True, 'message': 'Cleanup completed'}
    except Exception as e:
        logger.error(f"Failed to cleanup old task statuses: {str(e)}")
        return {'success': False, 'message': f'Cleanup failed: {str(e)}'}


# Utility functions for task management
def submit_ocr_task(file_data: bytes, filename: str, content_type: str,
                   language: str = 'en', extract_format: str = 'text',
                   confidence_threshold: float = 0.8,
                   voice_gender: str = 'male',
                   user_metadata: Optional[Dict] = None) -> str:
    """
    Submit an OCR processing task to the background queue.
    
    Returns:
        str: Task ID for tracking
    """
    task = process_ocr_upload.delay(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        language=language,
        extract_format=extract_format,
        confidence_threshold=confidence_threshold,
        user_metadata=user_metadata,
        voice_gender=voice_gender
    )
    
    logger.info(f"Submitted OCR task: {task.id} for file: {filename}")
    return task.id


def get_ocr_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an OCR processing task.
    
    Returns:
        Dict[str, Any]: Task status and results
    """
    try:
        # First check cache for real-time updates
        cache_key = f"ocr_task_{task_id}"
        cached_status = cache.get(cache_key)
        
        if cached_status:
            return cached_status
        
        # Query django-celery-results database directly for better performance
        try:
            from django_celery_results.models import TaskResult
            
            task_result = TaskResult.objects.filter(task_id=task_id).first()
            if task_result:
                # Parse result data
                result_data = {}
                if task_result.result:
                    try:
                        if isinstance(task_result.result, str):
                            result_data = json.loads(task_result.result)
                        else:
                            result_data = task_result.result
                    except (json.JSONDecodeError, TypeError):
                        result_data = {'raw_result': str(task_result.result)}
                
                return {
                    'task_id': task_id,
                    'status': task_result.status,
                    'progress': result_data.get('progress', 0) if isinstance(result_data, dict) else 0,
                    'message': result_data.get('message', '') if isinstance(result_data, dict) else '',
                    'result': result_data if isinstance(result_data, dict) else {},
                    'modified_at': task_result.date_done.isoformat() if task_result.date_done else task_result.date_created.isoformat(),
                    'created_at': task_result.date_created.isoformat(),
                    'task_name': task_result.task_name or 'unknown',
                    'worker': task_result.worker or 'unknown'
                }
        except ImportError:
            logger.warning("django_celery_results not available")
        except Exception as e:
            logger.error(f"Error querying django_celery_results directly: {str(e)}")
        
        # Fallback to calling the Celery task (less efficient but works)
        return get_ocr_task_status.delay(task_id).get()
        
    except Exception as e:
        logger.error(f"Failed to get OCR task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'progress': 0,
            'message': f'Failed to retrieve task status: {str(e)}',
            'result': {},
            'modified_at': datetime.now().isoformat()
        }


# Utility functions for TTS task management
def submit_tts_task(text: str, language_code: str = 'en',
                   voice_gender: str = 'female', voice_index: int = 0,
                   audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                   pitch: float = 0.0, volume_gain_db: float = 0.0,
                   file_prefix: str = 'tts_audio',
                   user_metadata: Optional[Dict] = None) -> str:
    """
    Submit a TTS processing task to the background queue.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        file_prefix (str): Prefix for generated filename
        user_metadata (dict): Additional user metadata
    
    Returns:
        str: Task ID for tracking
    """
    task = process_tts_generation.delay(
        text=text,
        language_code=language_code,
        voice_gender=voice_gender,
        voice_index=voice_index,
        audio_encoding=audio_encoding,
        speaking_rate=speaking_rate,
        pitch=pitch,
        volume_gain_db=volume_gain_db,
        file_prefix=file_prefix,
        user_metadata=user_metadata
    )
    
    logger.info(f"Submitted TTS task: {task.id} for text length: {len(text)}")
    return task.id


def get_tts_task_status_sync(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a TTS processing task synchronously.
    
    Args:
        task_id (str): Task ID
        
    Returns:
        Dict[str, Any]: Task status and results
    """
    try:
        # First check cache for real-time updates
        cache_key = f"tts_task_{task_id}"
        cached_status = cache.get(cache_key)
        
        if cached_status:
            return cached_status
        
        # Query django-celery-results database directly for better performance
        try:
            from django_celery_results.models import TaskResult
            
            task_result = TaskResult.objects.filter(task_id=task_id).first()
            if task_result:
                # Parse result data
                result_data = {}
                if task_result.result:
                    try:
                        if isinstance(task_result.result, str):
                            result_data = json.loads(task_result.result)
                        else:
                            result_data = task_result.result
                    except (json.JSONDecodeError, TypeError):
                        result_data = {'raw_result': str(task_result.result)}
                
                return {
                    'task_id': task_id,
                    'status': task_result.status,
                    'progress': result_data.get('progress', 0) if isinstance(result_data, dict) else 0,
                    'message': result_data.get('message', '') if isinstance(result_data, dict) else '',
                    'result': result_data if isinstance(result_data, dict) else {},
                    'modified_at': task_result.date_done.isoformat() if task_result.date_done else task_result.date_created.isoformat(),
                    'created_at': task_result.date_created.isoformat(),
                    'task_name': task_result.task_name or 'unknown',
                    'worker': task_result.worker or 'unknown'
                }
        except ImportError:
            logger.warning("django_celery_results not available")
        except Exception as e:
            logger.error(f"Error querying django_celery_results directly: {str(e)}")
        
        # Fallback to calling the Celery task (less efficient but works)
        return get_tts_task_status.delay(task_id).get()
        
    except Exception as e:
        logger.error(f"Failed to get TTS task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'progress': 0,
            'message': f'Failed to retrieve task status: {str(e)}',
            'result': {},
            'modified_at': datetime.now().isoformat()
        }


def quick_tts_task(text: str, language: str = 'en', gender: str = 'female') -> str:
    """
    Quick helper to submit a TTS task with default settings.
    
    Args:
        text (str): Text to synthesize
        language (str): Language code ('id' for Indonesian, 'en' for English)
        gender (str): Voice gender ('male' or 'female')
    
    Returns:
        str: Task ID
    """
    return submit_tts_task(
        text=text,
        language_code=language,
        voice_gender=gender,
        audio_encoding='mp3',
        file_prefix='quick_tts'
    )


# Add these new Celery tasks after the existing tasks

@shared_task(bind=True, ignore_result=False, max_retries=3, default_retry_delay=60)
def process_tts_streaming_generation(self, text: str, language_code: str = 'en',
                                   voice_gender: str = 'female', voice_index: int = 0,
                                   audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                                   pitch: float = 0.0, volume_gain_db: float = 0.0,
                                   use_ssml: bool = False, file_prefix: str = 'streaming_tts',
                                   save_to_gcs: bool = True,
                                   user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Background task to generate streaming text-to-speech audio and upload to Google Cloud Storage.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category (0-1)
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        use_ssml (bool): Whether text contains SSML markup
        file_prefix (str): Prefix for generated filename
        save_to_gcs (bool): Whether to save to Google Cloud Storage
        user_metadata (dict): Additional metadata from user
        
    Returns:
        Dict[str, Any]: Processing results
    """
    task_id = self.request.id
    request_id = f"tts_streaming_task_{task_id}_{int(datetime.now().timestamp() * 1000)}"
    
    logger.info(f"[{request_id}] Starting background TTS streaming generation task: {task_id}")
    
    try:
        # Insert voice gender to the user metadata for tracking
        if user_metadata is not None:
            user_metadata['voice_gender'] = voice_gender

        # Initialize progress tracking
        tts_streaming_task_processor.update_task_status(
            task_id, 'PROCESSING', 0, 
            'Initializing TTS streaming processing...'
        )
        
        # Check if task processor is ready
        if not tts_streaming_task_processor.is_ready():
            error_msg = "Google Text-to-Speech Streaming service not available"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_streaming_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'retry_count': self.request.retries}
            )
            
            # Retry if not at max retries
            if self.request.retries < self.max_retries:
                logger.info(f"[{request_id}] Retrying in {self.default_retry_delay} seconds")
                raise self.retry(countdown=self.default_retry_delay)
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'synthesis_method': 'streaming',
                'user_metadata': user_metadata or {}
            }
        
        # Validate text input
        if not text or len(text.strip()) == 0:
            error_msg = "Text input is required and cannot be empty"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_streaming_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'text_length': len(text) if text else 0}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'user_metadata': user_metadata or {},
                'synthesis_method': 'streaming'
            }
        
        # Check text length limits for streaming (higher limit than regular TTS)
        text_length = len(text)
        if text_length > 50000:  # Streaming can handle larger texts
            error_msg = f"Text too long for streaming: {text_length} characters (max 50000)"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_streaming_task_processor.update_task_status(
                task_id, 'FAILURE', 0, error_msg,
                {'error': error_msg, 'text_length': text_length}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'text_length': text_length,
                'user_metadata': user_metadata or {},
                'synthesis_method': 'streaming'
            }
        
        # Estimate processing time for user information
        estimated_time = tts_streaming_task_processor.tts_streaming_client.estimate_synthesis_time(
            text, speaking_rate
        )
        
        # Step 1: Start streaming synthesis (30% progress)
        tts_streaming_task_processor.update_task_status(
            task_id, 'PROCESSING', 30,
            f'Starting streaming synthesis: {len(text)} characters, estimated {estimated_time:.1f}s'
        )
        
        streaming_start_time = datetime.now()
        
        # Create progress callback for streaming updates
        def streaming_progress_callback(progress: int, total_chunks: int):
            # Update progress between 30% and 90%
            streaming_progress = 30 + int((progress / 100) * 60)  # 30% to 90%
            tts_streaming_task_processor.update_task_status(
                task_id, 'PROCESSING', streaming_progress,
                f'Streaming synthesis: {progress}% complete ({total_chunks} chunks)'
            )
        
        try:
            streaming_result = tts_streaming_task_processor.tts_streaming_client.synthesize_and_save_streaming(
                text=text,
                language_code=language_code,
                voice_gender=voice_gender,
                voice_index=voice_index,
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db,
                use_ssml=use_ssml,
                file_prefix=file_prefix,
                save_to_gcs=save_to_gcs,
                progress_callback=streaming_progress_callback,
                user_metadata=user_metadata
            )
            
            streaming_processing_time = (datetime.now() - streaming_start_time).total_seconds()
            
            if not streaming_result.get('synthesis_completed', False):
                error_msg = f"TTS streaming synthesis failed: {streaming_result.get('error', 'Unknown error')}"
                logger.error(f"[{request_id}] {error_msg}")
                
                tts_streaming_task_processor.update_task_status(
                    task_id, 'FAILURE', 90, error_msg,
                    {
                        'error': error_msg,
                        'streaming_result': streaming_result,
                        'text_length': text_length
                    }
                )
                
                return {
                    'success': False,
                    'message': error_msg,
                    'task_id': task_id,
                    'processing_id': request_id,
                    'streaming_result': streaming_result,
                    'text_length': text_length,
                    'user_metadata': user_metadata or {},
                    'synthesis_method': 'streaming'
                }
            
        except Exception as e:
            error_msg = f"TTS streaming generation failed: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_streaming_task_processor.update_task_status(
                task_id, 'FAILURE', 50, error_msg,
                {
                    'error': error_msg,
                    'exception_type': type(e).__name__,
                    'text_length': text_length
                }
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'text_length': text_length,
                'user_metadata': user_metadata or {},
                'synthesis_method': 'streaming'
            }
        
        logger.info(f"[{request_id}] TTS streaming generation completed successfully in {streaming_processing_time:.2f}s")
        
        # Step 2: Finalize results (100% progress)
        tts_streaming_task_processor.update_task_status(
            task_id, 'PROCESSING', 95,
            'Finalizing streaming TTS results and metadata'
        )
        
        # Prepare comprehensive results
        final_result = {
            'success': True,
            'message': 'Text-to-speech streaming generation completed successfully',
            'task_id': task_id,
            'processing_id': request_id,
            'text_info': {
                'original_text': text[:500] + '...' if len(text) > 500 else text,  # Truncate for display
                'text_length': text_length,
                'language': language_code,
                'voice_gender': voice_gender,
                'voice_index': voice_index,
                'voice_name': streaming_result['metadata']['voice_name'],
                'use_ssml': use_ssml
            },
            'audio_info': {
                'format': audio_encoding,
                'size_bytes': streaming_result.get('file_size_bytes', 0),
                'size_mb': round(streaming_result.get('file_size_bytes', 0) / (1024 * 1024), 2),
                'duration_estimate_seconds': streaming_result.get('duration_estimate_seconds', 0),
                'speaking_rate': speaking_rate,
                'pitch': pitch,
                'volume_gain_db': volume_gain_db,
                'chunks_processed': streaming_result['metadata']['chunks_processed']
            },
            'storage_info': {
                'storage_type': streaming_result.get('storage_type', 'unknown'),
                'file_path': streaming_result.get('file_path'),
                'file_url': streaming_result.get('file_url'),
                'filename': streaming_result.get('filename'),
                'gcs_blob_name': streaming_result.get('gcs_blob_name'),
                'gcs_path': streaming_result.get('gcs_path')
            },
            'processing_info': {
                'processing_time_seconds': round(streaming_processing_time, 2),
                'estimated_time_seconds': round(estimated_time, 2),
                'processed_at': datetime.now().isoformat(),
                'task_started_at': self.request.eta.isoformat() if self.request.eta else None,
                'file_prefix': file_prefix,
                'synthesis_method': 'streaming'
            },
            'metadata': streaming_result.get('metadata', {}),
            'user_metadata': user_metadata or {}
        }
        
        # Step 3: Complete (100% progress)
        tts_streaming_task_processor.update_task_status(
            task_id, 'SUCCESS', 100,
            'TTS streaming generation completed successfully',
            final_result
        )
        
        logger.info(f"[{request_id}] Background TTS streaming task completed successfully")
        
        return final_result
        
    except Retry:
        # Re-raise retry exceptions
        raise
    except Exception as e:
        error_msg = f"Unexpected error in background TTS streaming task: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        
        tts_streaming_task_processor.update_task_status(
            task_id, 'FAILURE', 0, error_msg,
            {
                'error': error_msg,
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries,
                'synthesis_method': 'streaming'
            }
        )
        
        return {
            'success': False,
            'message': error_msg,
            'task_id': task_id,
            'processing_id': request_id,
            'error_details': {
                'exception_type': type(e).__name__,
                'retry_count': self.request.retries
            },
            'user_metadata': user_metadata or {},
            'synthesis_method': 'streaming'
        }


@shared_task(bind=True, ignore_result=False, max_retries=2, default_retry_delay=30)
def process_tts_streaming_chunks(self, text: str, language_code: str = 'en',
                               voice_gender: str = 'female', voice_index: int = 0,
                               audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                               pitch: float = 0.0, volume_gain_db: float = 0.0,
                               use_ssml: bool = False,
                               chunk_callback_url: Optional[str] = None,
                               user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Background task to generate TTS with real-time chunk delivery via callback URL.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        use_ssml (bool): Whether text contains SSML markup
        chunk_callback_url (str): URL to POST audio chunks to
        user_metadata (dict): Additional metadata from user
        
    Returns:
        Dict[str, Any]: Processing results
    """
    task_id = self.request.id
    request_id = f"tts_chunk_task_{task_id}_{int(datetime.now().timestamp() * 1000)}"
    
    logger.info(f"[{request_id}] Starting background TTS chunk streaming task: {task_id}")
    
    try:
        # Initialize progress tracking
        tts_streaming_task_processor.update_task_status(
            task_id, 'PROCESSING', 0, 
            'Initializing TTS chunk streaming...'
        )
        
        # Check if task processor is ready
        if not tts_streaming_task_processor.is_ready():
            error_msg = "Google Text-to-Speech Streaming service not available"
            logger.error(f"[{request_id}] {error_msg}")
            raise self.retry(countdown=self.default_retry_delay)
        
        # Validate inputs
        if not text or len(text.strip()) == 0:
            return {
                'success': False,
                'message': 'Text input is required',
                'task_id': task_id,
                'synthesis_method': 'chunk_streaming'
            }
        
        text_length = len(text)
        chunks_sent = 0
        total_audio_size = 0
        
        # Create callback function for chunk delivery
        def chunk_delivery_callback(chunk_index: int, total_chunks: int, chunk_data: bytes):
            nonlocal chunks_sent, total_audio_size
            
            chunks_sent += 1
            total_audio_size += len(chunk_data)
            
            # Update progress
            progress = int((chunk_index / total_chunks) * 90)  # Reserve 10% for finalization
            tts_streaming_task_processor.update_task_status(
                task_id, 'PROCESSING', progress,
                f'Streaming chunk {chunk_index}/{total_chunks} ({len(chunk_data)} bytes)'
            )
            
            # Send chunk to callback URL if provided
            if chunk_callback_url:
                try:
                    chunk_data_payload = {
                        'task_id': task_id,
                        'chunk_index': chunk_index,
                        'total_chunks': total_chunks,
                        'chunk_size': len(chunk_data),
                        'audio_data': chunk_data.hex(),  # Send as hex string
                        'metadata': {
                            'language_code': language_code,
                            'voice_gender': voice_gender,
                            'audio_encoding': audio_encoding
                        }
                    }
                    
                    response = requests.post(
                        chunk_callback_url,
                        json=chunk_data_payload,
                        timeout=10,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        logger.debug(f"[{request_id}] Chunk {chunk_index} delivered successfully")
                    else:
                        logger.warning(f"[{request_id}] Chunk {chunk_index} delivery failed: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"[{request_id}] Failed to deliver chunk {chunk_index}: {str(e)}")
        
        # Perform streaming synthesis with chunk delivery
        streaming_start_time = datetime.now()
        
        try:
            # Stream audio chunks with callback
            for chunk_data in tts_streaming_task_processor.tts_streaming_client.synthesize_streaming(
                text=text,
                language_code=language_code,
                voice_gender=voice_gender,
                voice_index=voice_index,
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db,
                use_ssml=use_ssml,
                progress_callback=chunk_delivery_callback,
                user_metadata=user_metadata
            ):
                pass  # Chunks are handled in the callback
                
        except Exception as e:
            error_msg = f"TTS chunk streaming failed: {str(e)}"
            logger.error(f"[{request_id}] {error_msg}")
            
            tts_streaming_task_processor.update_task_status(
                task_id, 'FAILURE', 50, error_msg,
                {'error': error_msg, 'chunks_sent': chunks_sent}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'chunks_sent': chunks_sent,
                'synthesis_method': 'chunk_streaming'
            }
        
        streaming_processing_time = (datetime.now() - streaming_start_time).total_seconds()
        
        # Finalize results
        final_result = {
            'success': True,
            'message': 'TTS chunk streaming completed successfully',
            'task_id': task_id,
            'processing_id': request_id,
            'streaming_info': {
                'chunks_sent': chunks_sent,
                'total_audio_size_bytes': total_audio_size,
                'total_audio_size_mb': round(total_audio_size / (1024 * 1024), 2),
                'processing_time_seconds': round(streaming_processing_time, 2),
                'callback_url': chunk_callback_url,
                'synthesis_method': 'chunk_streaming'
            },
            'text_info': {
                'text_length': text_length,
                'language_code': language_code,
                'voice_gender': voice_gender,
                'voice_index': voice_index
            },
            'user_metadata': user_metadata or {}
        }
        
        # Complete task
        tts_streaming_task_processor.update_task_status(
            task_id, 'SUCCESS', 100,
            'TTS chunk streaming completed successfully',
            final_result
        )
        
        logger.info(f"[{request_id}] TTS chunk streaming task completed: {chunks_sent} chunks sent")
        
        return final_result
        
    except Retry:
        raise
    except Exception as e:
        error_msg = f"Unexpected error in TTS chunk streaming task: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}", exc_info=True)
        
        return {
            'success': False,
            'message': error_msg,
            'task_id': task_id,
            'processing_id': request_id,
            'synthesis_method': 'chunk_streaming'
        }


@shared_task
def get_tts_streaming_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of a TTS streaming processing task.
    
    Args:
        task_id (str): Celery task ID
        
    Returns:
        Dict[str, Any]: Task status information
    """
    try:
        # First check cache for real-time status updates
        cache_key = f"tts_streaming_task_{task_id}"
        status_data = cache.get(cache_key)
        
        if status_data:
            return status_data
        
        # Fallback to regular TTS task status check
        return get_tts_task_status_sync(task_id)
        
    except Exception as e:
        logger.error(f"Failed to get TTS streaming task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'progress': 0,
            'message': f'Failed to retrieve streaming task status: {str(e)}',
            'result': {},
            'synthesis_method': 'streaming',
            'modified_at': datetime.now().isoformat()
        }


# Add these utility functions after the existing ones

def submit_tts_streaming_task(text: str, language_code: str = 'en',
                            voice_gender: str = 'female', voice_index: int = 0,
                            audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                            pitch: float = 0.0, volume_gain_db: float = 0.0,
                            use_ssml: bool = False, file_prefix: str = 'streaming_tts',
                            save_to_gcs: bool = True,
                            user_metadata: Optional[Dict] = None) -> str:
    """
    Submit a TTS streaming processing task to the background queue.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        use_ssml (bool): Whether text contains SSML markup
        file_prefix (str): Prefix for generated filename
        save_to_gcs (bool): Whether to save to Google Cloud Storage
        user_metadata (dict): Additional user metadata
    
    Returns:
        str: Task ID for tracking
    """
    task = process_tts_streaming_generation.delay(
        text=text,
        language_code=language_code,
        voice_gender=voice_gender,
        voice_index=voice_index,
        audio_encoding=audio_encoding,
        speaking_rate=speaking_rate,
        pitch=pitch,
        volume_gain_db=volume_gain_db,
        use_ssml=use_ssml,
        file_prefix=file_prefix,
        save_to_gcs=save_to_gcs,
        user_metadata=user_metadata
    )
    
    logger.info(f"Submitted TTS streaming task: {task.id} for text length: {len(text)}")
    return task.id


def submit_tts_chunk_streaming_task(text: str, language_code: str = 'en',
                                  voice_gender: str = 'female', voice_index: int = 0,
                                  audio_encoding: str = 'mp3', speaking_rate: float = 1.0,
                                  pitch: float = 0.0, volume_gain_db: float = 0.0,
                                  use_ssml: bool = False,
                                  chunk_callback_url: Optional[str] = None,
                                  user_metadata: Optional[Dict] = None) -> str:
    """
    Submit a TTS chunk streaming task for real-time audio delivery.
    
    Args:
        text (str): Text to synthesize
        language_code (str): Language code ('id', 'en', 'en-GB')
        voice_gender (str): Voice gender ('male' or 'female')
        voice_index (int): Voice index within gender category
        audio_encoding (str): Output audio format ('mp3', 'wav', 'ogg')
        speaking_rate (float): Speaking rate (0.25 to 4.0)
        pitch (float): Pitch adjustment (-20.0 to 20.0 semitones)
        volume_gain_db (float): Volume gain (-96.0 to 16.0 dB)
        use_ssml (bool): Whether text contains SSML markup
        chunk_callback_url (str): URL to POST audio chunks to
        user_metadata (dict): Additional user metadata
    
    Returns:
        str: Task ID for tracking
    """
    task = process_tts_streaming_chunks.delay(
        text=text,
        language_code=language_code,
        voice_gender=voice_gender,
        voice_index=voice_index,
        audio_encoding=audio_encoding,
        speaking_rate=speaking_rate,
        pitch=pitch,
        volume_gain_db=volume_gain_db,
        use_ssml=use_ssml,
        chunk_callback_url=chunk_callback_url,
        user_metadata=user_metadata
    )
    
    logger.info(f"Submitted TTS chunk streaming task: {task.id} for text length: {len(text)}")
    return task.id


def get_tts_streaming_task_status_sync(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a TTS streaming processing task synchronously.
    
    Args:
        task_id (str): Task ID
        
    Returns:
        Dict[str, Any]: Task status and results
    """
    try:
        # Check streaming-specific cache first
        cache_key = f"tts_streaming_task_{task_id}"
        cached_status = cache.get(cache_key)
        
        if cached_status:
            return cached_status
        
        # Fallback to regular TTS status
        return get_tts_task_status_sync(task_id)
        
    except Exception as e:
        logger.error(f"Failed to get TTS streaming task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'progress': 0,
            'message': f'Failed to retrieve streaming task status: {str(e)}',
            'result': {},
            'synthesis_method': 'streaming',
            'modified_at': datetime.now().isoformat()
        }


def quick_tts_streaming_task(text: str, language: str = 'en', gender: str = 'female') -> str:
    """
    Quick helper to submit a TTS streaming task with default settings.
    
    Args:
        text (str): Text to synthesize
        language (str): Language code ('id' for Indonesian, 'en' for English)
        gender (str): Voice gender ('male' or 'female')
    
    Returns:
        str: Task ID
    """
    return submit_tts_streaming_task(
        text=text,
        language_code=language,
        voice_gender=gender,
        audio_encoding='mp3',
        file_prefix='quick_streaming_tts'
    )
