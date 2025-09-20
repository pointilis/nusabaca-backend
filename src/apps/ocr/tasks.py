import os
import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from celery import shared_task, current_task
from celery.exceptions import Retry
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.core.cache import cache

from apps.ocr.lib.google_vision import GoogleCloudVision
from apps.ocr.lib.google_storage import GoogleCloudStorage

# Configure logger
logger = logging.getLogger(__name__)


class OCRTaskProcessor:
    """
    Class to handle OCR processing tasks with Google Cloud services.
    Manages file uploads to Google Storage and text recognition in background.
    """
    
    def __init__(self):
        # Store configuration variables
        self.bucket_name = getattr(settings, 'GCS_BUCKET_NAME', os.getenv('GCS_BUCKET_NAME'))
        self.service_account_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', 
                                          os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        self.project_id = getattr(settings, 'GCS_PROJECT_ID', os.getenv('GCS_PROJECT_ID'))
        
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
            self.vision_client = GoogleCloudVision(self.service_account_path)
            
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
                'updated_at': datetime.now().isoformat(),
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


# Global task processor instance
task_processor = OCRTaskProcessor()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_upload(self, file_data: bytes, filename: str, content_type: str,
                      language: str = 'en', extract_format: str = 'text',
                      confidence_threshold: float = 0.8,
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
        task_processor.update_task_status(
            task_id, 'PROCESSING', 0, 
            'Initializing OCR processing...'
        )
        
        # Check if task processor is ready
        if not task_processor.is_ready():
            error_msg = "Google Cloud services not available"
            logger.error(f"[{request_id}] {error_msg}")
            
            task_processor.update_task_status(
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
        timestamp = datetime.now().strftime('%Y/%m/%d')
        file_extension = os.path.splitext(filename)[1].lower()
        clean_filename = os.path.splitext(filename)[0][:50]
        
        uploaded_file_path = f"uploads/{timestamp}/{request_id}_{clean_filename}{file_extension}"
        results_file_path = f"results/{timestamp}/{request_id}_results.json"
        
        # Step 1: Upload file to Google Cloud Storage (20% progress)
        task_processor.update_task_status(
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
        
        storage_upload_result = task_processor.storage_client.upload_from_memory(
            file_data=file_data,
            destination_blob_name=uploaded_file_path,
            content_type=content_type,
            metadata=upload_metadata
        )
        
        if not storage_upload_result['success']:
            error_msg = f"Failed to upload file to storage: {storage_upload_result['message']}"
            logger.error(f"[{request_id}] {error_msg}")
            
            task_processor.update_task_status(
                task_id, 'FAILURE', 20, error_msg,
                {'error': error_msg, 'storage_result': storage_upload_result}
            )
            
            return {
                'success': False,
                'message': error_msg,
                'task_id': task_id,
                'processing_id': request_id,
                'storage_info': storage_upload_result
            }
        
        logger.info(f"[{request_id}] File uploaded successfully: {uploaded_file_path}")
        
        # Step 2: Process OCR (40% progress)
        task_processor.update_task_status(
            task_id, 'PROCESSING', 40,
            f'Processing OCR with format: {extract_format}'
        )
        
        ocr_start_time = datetime.now()
        
        # Perform OCR based on format
        if extract_format == 'structured':
            logger.info(f"[{request_id}] Starting structured document OCR processing")
            ocr_result = task_processor.vision_client.detect_document_text(file_data)
        else:
            logger.info(f"[{request_id}] Starting standard text OCR processing")
            ocr_result = task_processor.vision_client.detect_text(file_data)
        
        ocr_processing_time = (datetime.now() - ocr_start_time).total_seconds()
        
        if not ocr_result['success']:
            error_msg = f"OCR processing failed: {ocr_result['message']}"
            logger.error(f"[{request_id}] {error_msg}")
            
            task_processor.update_task_status(
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
                'storage_info': storage_upload_result
            }
        
        logger.info(f"[{request_id}] OCR processing completed successfully in {ocr_processing_time:.2f}s")
        
        # Step 3: Store results (70% progress)
        task_processor.update_task_status(
            task_id, 'PROCESSING', 70,
            'Storing OCR results to Google Cloud Storage'
        )
        
        # Prepare comprehensive results
        results_data = {
            'processing_id': request_id,
            'task_id': task_id,
            'original_file': {
                'name': filename,
                'size': len(file_data),
                'content_type': content_type,
                'gcs_path': uploaded_file_path,
                'gs_url': storage_upload_result['gs_url']
            },
            'processing_info': {
                'language': language,
                'extract_format': extract_format,
                'confidence_threshold': confidence_threshold,
                'processing_time': round(ocr_processing_time, 2),
                'processed_at': datetime.now().isoformat(),
                'task_started_at': self.request.eta.isoformat() if self.request.eta else None
            },
            'ocr_results': ocr_result,
            'metadata': user_metadata or {}
        }
        
        results_json = json.dumps(results_data, indent=2, ensure_ascii=False)
        
        results_upload = task_processor.storage_client.upload_from_memory(
            file_data=results_json.encode('utf-8'),
            destination_blob_name=results_file_path,
            content_type='application/json',
            metadata={
                'request_id': request_id,
                'task_id': task_id,
                'result_type': 'ocr_results',
                'original_file': filename,
                'processing_time': str(round(ocr_processing_time, 2)),
                'text_length': str(len(ocr_result.get('full_text', '')))
            }
        )
        
        if not results_upload['success']:
            logger.warning(f"[{request_id}] Failed to store results: {results_upload['message']}")
        
        # Step 4: Generate signed URLs (90% progress)
        task_processor.update_task_status(
            task_id, 'PROCESSING', 90,
            'Generating secure access URLs'
        )
        
        # Generate signed URLs for temporary access
        signed_url_result = None
        results_signed_url = None
        
        try:
            # Original file signed URL (1 hour)
            signed_url_result = task_processor.storage_client.generate_signed_url(
                uploaded_file_path, expiration_minutes=60
            )
            
            # Results file signed URL (24 hours)
            if results_upload['success']:
                results_signed_url = task_processor.storage_client.generate_signed_url(
                    results_file_path, expiration_minutes=1440
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
                'original_file': {
                    'gcs_path': uploaded_file_path,
                    'gs_url': storage_upload_result['gs_url'],
                    'signed_url': signed_url_result['signed_url'] if signed_url_result and signed_url_result['success'] else None,
                    'signed_url_expires_at': signed_url_result['expires_at'] if signed_url_result and signed_url_result['success'] else None
                },
                'results_file': {
                    'gcs_path': results_file_path if results_upload['success'] else None,
                    'gs_url': results_upload['gs_url'] if results_upload['success'] else None,
                    'signed_url': results_signed_url['signed_url'] if results_signed_url and results_signed_url['success'] else None,
                    'signed_url_expires_at': results_signed_url['expires_at'] if results_signed_url and results_signed_url['success'] else None,
                    'size': results_upload['size'] if results_upload['success'] else None
                }
            },
            'ocr_result': {
                'full_text': ocr_result.get('full_text', ''),
                'confidence': confidence_threshold,
                'processing_time': round(ocr_processing_time, 2),
                'language': language,
                'format': extract_format,
                'text_blocks_count': len(ocr_result.get('text_blocks', [])) if extract_format == 'json' else None,
                'pages_count': len(ocr_result.get('pages', [])) if extract_format == 'structured' else None
            },
            'processing_completed_at': datetime.now().isoformat()
        }
        
        # Add format-specific data
        if extract_format == 'json' and 'text_blocks' in ocr_result:
            final_result['ocr_result']['text_blocks'] = ocr_result['text_blocks']
        elif extract_format == 'structured' and 'pages' in ocr_result:
            final_result['ocr_result']['pages'] = ocr_result['pages']
        
        # Update final status
        task_processor.update_task_status(
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
        
        task_processor.update_task_status(
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
            }
        }


@shared_task
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the current status of an OCR processing task.
    
    Args:
        task_id (str): Celery task ID
        
    Returns:
        Dict[str, Any]: Task status information
    """
    try:
        cache_key = f"ocr_task_{task_id}"
        status_data = cache.get(cache_key)
        
        if status_data:
            return status_data
        
        # Fallback to Celery task state
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'progress': result.info.get('progress', 0) if result.info else 0,
            'message': result.info.get('message', '') if result.info else '',
            'result': result.info.get('result', {}) if result.info else {},
            'updated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {str(e)}")
        return {
            'task_id': task_id,
            'status': 'UNKNOWN',
            'progress': 0,
            'message': f'Failed to retrieve task status: {str(e)}',
            'result': {},
            'updated_at': datetime.now().isoformat()
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
        user_metadata=user_metadata
    )
    
    logger.info(f"Submitted OCR task: {task.id} for file: {filename}")
    return task.id


def get_ocr_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an OCR processing task.
    
    Returns:
        Dict[str, Any]: Task status and results
    """
    return get_task_status.delay(task_id).get()
