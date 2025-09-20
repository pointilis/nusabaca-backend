import os
import logging
import time
import uuid
from typing import Dict, Any
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.conf import settings

from .serializers import FileSerializer, FileUploadResponseSerializer
from apps.ocr.lib.google_vision import GoogleCloudVision
from apps.ocr.lib.google_storage import GoogleCloudStorage

# Configure logger for the upload views
logger = logging.getLogger(__name__)


class UploadAPIView(APIView):
    """
    API View for handling file uploads and OCR processing with Google Cloud Storage integration.
    """
    parser_classes = (MultiPartParser, FormParser)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.root_path = settings.BASE_DIR.parent.parent
        # Initialize Google Cloud clients
        self.storage_client = None
        self.vision_client = None
        self.project_id = getattr(settings, 'GOOGLE_CLOUD_PROJECT_ID', os.getenv('GOOGLE_CLOUD_PROJECT_ID'))
        self.bucket_name = getattr(settings, 'GOOGLE_CLOUD_STORAGE_BUCKET', os.getenv('GOOGLE_CLOUD_STORAGE_BUCKET'))
        self.service_account_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
        self._init_storage_client()
        self._init_vision_client()
    
    def _init_storage_client(self):
        """Initialize Google Cloud Storage client with configuration."""
        try:
            if self.bucket_name:
                self.storage_client = GoogleCloudStorage(
                    bucket_name=self.bucket_name,
                    service_account_path=self.service_account_path,
                    project_id=self.project_id
                )
                logger.info("Google Cloud Storage client initialized successfully")
            else:
                logger.warning("GCS bucket name not configured. Storage features will be disabled.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage: {str(e)}")
            self.storage_client = None
    
    def _init_vision_client(self):
        """Initialize Google Cloud Vision client with configuration."""
        try:
            self.vision_client = GoogleCloudVision(self.service_account_path)
            
            if self.vision_client.is_client_ready():
                logger.info("Google Cloud Vision client initialized successfully")
            else:
                logger.error("Google Cloud Vision client initialization failed - client not ready")
                self.vision_client = None
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Vision: {str(e)}")
            self.vision_client = None

    def post(self, request, *args, **kwargs) -> Response:
        """
        Handle POST request for file upload and OCR processing with cloud storage integration.
        
        Pipeline:
        1. Validate uploaded file
        2. Upload file to Google Cloud Storage
        3. Process file with OCR using Google Vision
        4. Store OCR results with file references
        5. Return comprehensive response with storage URLs
        
        Args:
            request: HTTP request object containing the uploaded file
            
        Returns:
            Response: JSON response with OCR results and storage information
        """
        start_time = time.time()
        request_id = f"req_{uuid.uuid4().hex[:8]}_{int(start_time * 1000)}"
        uploaded_file_path = None
        results_file_path = None
        
        logger.info(f"[{request_id}] Starting OCR pipeline request from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        try:
            # Validate the uploaded file
            file_serializer = FileSerializer(data=request.data)
            
            if not file_serializer.is_valid():
                logger.warning(f"[{request_id}] File validation failed: {file_serializer.errors}")
                return Response(
                    {
                        'success': False,
                        'message': 'File validation failed',
                        'errors': file_serializer.errors,
                        'processing_id': request_id
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = file_serializer.validated_data['file']
            language = file_serializer.validated_data.get('language', 'en')
            extract_format = file_serializer.validated_data.get('extract_format', 'text')
            confidence_threshold = file_serializer.validated_data.get('confidence_threshold', 0.8)
            
            logger.info(f"[{request_id}] Processing file: {file.name} ({file.size} bytes), "
                       f"language: {language}, format: {extract_format}")
            
            # Generate unique file paths for cloud storage
            timestamp = datetime.now().strftime('%Y/%m/%d')
            file_extension = os.path.splitext(file.name)[1].lower()
            clean_filename = os.path.splitext(file.name)[0][:50]  # Limit filename length
            
            uploaded_file_path = f"uploads/{timestamp}/{request_id}_{clean_filename}{file_extension}"
            results_file_path = f"results/{timestamp}/{request_id}_results.json"
            
            # Step 1: Upload file to Google Cloud Storage
            storage_upload_result = None
            if self.storage_client and self.storage_client.is_client_ready():
                logger.info(f"[{request_id}] Uploading file to Google Cloud Storage: {uploaded_file_path}")
                
                # Upload from memory for efficiency
                file.seek(0)  # Reset file pointer
                file_content = file.read()
                file.seek(0)  # Reset again for potential local processing
                
                storage_upload_result = self.storage_client.upload_from_memory(
                    file_data=file_content,
                    destination_blob_name=uploaded_file_path,
                    content_type=file.content_type,
                    metadata={
                        'request_id': request_id,
                        'original_filename': file.name,
                        'upload_timestamp': datetime.now().isoformat(),
                        'language': language,
                        'extract_format': extract_format,
                        'user_ip': request.META.get('REMOTE_ADDR', 'unknown')
                    }
                )
                
                if storage_upload_result['success']:
                    logger.info(f"[{request_id}] File uploaded to GCS successfully")
                else:
                    logger.warning(f"[{request_id}] GCS upload failed: {storage_upload_result['message']}")
            
            # Step 2: Process with OCR (use GCS file if available, otherwise use local temp file)
            ocr_result = None
            temp_file_path = None
            
            try:
                # Check if Google Cloud Vision client is ready
                if not self.vision_client or not self.vision_client.is_client_ready():
                    logger.error(f"[{request_id}] Google Vision client not available or not ready")
                    return Response(
                        {
                            'success': False,
                            'message': 'OCR service not available',
                            'error': 'Vision client not ready or not initialized',
                            'processing_id': request_id
                        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                
                logger.debug(f"[{request_id}] Using pre-initialized Google Vision client")
                ocr_start_time = time.time()
                
                # Try to process from GCS first, fallback to local temp file
                if (storage_upload_result and storage_upload_result['success'] and 
                    self.storage_client and self.storage_client.is_client_ready()):
                    
                    logger.info(f"[{request_id}] Processing OCR from Google Cloud Storage")
                    
                    # Read file from GCS for OCR processing
                    gcs_file_result = self.storage_client.read_file(uploaded_file_path)
                    if gcs_file_result['success']:
                        file_content = gcs_file_result['content']
                        
                        if extract_format == 'structured':
                            logger.info(f"[{request_id}] Starting structured document OCR processing")
                            ocr_result = self.vision_client.detect_document_text(file_content)
                        else:
                            logger.info(f"[{request_id}] Starting standard text OCR processing")
                            ocr_result = self.vision_client.detect_text(file_content)
                    else:
                        logger.warning(f"[{request_id}] Failed to read file from GCS, falling back to local processing")
                
                # Fallback to local temporary file processing
                if ocr_result is None:
                    logger.info(f"[{request_id}] Processing OCR from local temporary file")
                    
                    # Save file locally as fallback
                    temp_file_path = default_storage.save(f'{self.root_path}/temp/{request_id}_{file.name}', file)
                    temp_file_full_path = default_storage.path(temp_file_path)
                    
                    if extract_format == 'structured':
                        ocr_result = self.vision_client.detect_document_text_from_file(temp_file_full_path)
                    else:
                        ocr_result = self.vision_client.detect_text_from_file(temp_file_full_path)
                
                ocr_processing_time = time.time() - ocr_start_time
                
                if ocr_result and ocr_result['success']:
                    logger.info(f"[{request_id}] OCR processing completed successfully in {ocr_processing_time:.2f}s")
                    logger.debug(f"[{request_id}] Extracted text length: {len(ocr_result.get('full_text', ''))}")
                    
                    # Step 3: Store OCR results in Google Cloud Storage
                    results_storage_info = None
                    if self.storage_client and self.storage_client.is_client_ready():
                        logger.info(f"[{request_id}] Storing OCR results to Google Cloud Storage")
                        
                        # Prepare comprehensive results data
                        results_data = {
                            'processing_id': request_id,
                            'original_file': {
                                'name': file.name,
                                'size': file.size,
                                'content_type': file.content_type,
                                'gcs_path': uploaded_file_path if storage_upload_result and storage_upload_result['success'] else None
                            },
                            'processing_info': {
                                'language': language,
                                'extract_format': extract_format,
                                'confidence_threshold': confidence_threshold,
                                'processing_time': round(ocr_processing_time, 2),
                                'timestamp': datetime.now().isoformat()
                            },
                            'ocr_results': ocr_result,
                            'metadata': {
                                'user_ip': request.META.get('REMOTE_ADDR', 'unknown'),
                                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')
                            }
                        }
                        
                        import json
                        results_json = json.dumps(results_data, indent=2, ensure_ascii=False)
                        
                        results_upload = self.storage_client.upload_from_memory(
                            file_data=results_json.encode('utf-8'),
                            destination_blob_name=results_file_path,
                            content_type='application/json',
                            metadata={
                                'request_id': request_id,
                                'result_type': 'ocr_results',
                                'original_file': file.name,
                                'processing_time': str(round(ocr_processing_time, 2))
                            }
                        )
                        
                        if results_upload['success']:
                            logger.info(f"[{request_id}] OCR results stored to GCS successfully")
                            results_storage_info = {
                                'gcs_path': results_file_path,
                                'gs_url': results_upload['gs_url'],
                                'size': results_upload['size']
                            }
                        else:
                            logger.warning(f"[{request_id}] Failed to store results to GCS: {results_upload['message']}")
                    
                    # Step 4: Prepare comprehensive response
                    response_data = {
                        'success': True,
                        'message': 'File processed successfully through OCR pipeline',
                        'processing_id': request_id,
                        'file_info': file_serializer.get_file_info(),
                        'storage_info': {
                            'original_file': {
                                'uploaded_to_gcs': storage_upload_result['success'] if storage_upload_result else False,
                                'gcs_path': uploaded_file_path if storage_upload_result and storage_upload_result['success'] else None,
                                'gs_url': storage_upload_result.get('gs_url') if storage_upload_result and storage_upload_result['success'] else None
                            },
                            'results_file': results_storage_info
                        },
                        'ocr_result': {
                            'full_text': ocr_result.get('full_text', ''),
                            'confidence': confidence_threshold,
                            'processing_time': round(ocr_processing_time, 2),
                            'language': language,
                            'format': extract_format,
                            'text_blocks_count': len(ocr_result.get('text_blocks', [])) if extract_format == 'json' else None,
                            'pages_count': len(ocr_result.get('pages', [])) if extract_format == 'structured' else None
                        }
                    }
                    
                    # Add format-specific data
                    if extract_format == 'json':
                        response_data['ocr_result']['text_blocks'] = ocr_result.get('text_blocks', [])
                    elif extract_format == 'structured':
                        response_data['ocr_result']['pages'] = ocr_result.get('pages', [])
                    
                    # Add signed URLs for temporary access if available
                    if self.storage_client and storage_upload_result and storage_upload_result['success']:
                        try:
                            signed_url_result = self.storage_client.generate_signed_url(
                                uploaded_file_path, 
                                expiration_minutes=60
                            )
                            if signed_url_result['success']:
                                response_data['storage_info']['original_file']['signed_url'] = signed_url_result['signed_url']
                                response_data['storage_info']['original_file']['signed_url_expires_at'] = signed_url_result['expires_at']
                        except Exception as e:
                            logger.warning(f"[{request_id}] Failed to generate signed URL: {str(e)}")
                    
                    total_processing_time = time.time() - start_time
                    response_data['total_processing_time'] = round(total_processing_time, 2)
                    
                    logger.info(f"[{request_id}] OCR pipeline completed successfully in {total_processing_time:.2f}s")
                    
                    return Response(response_data, status=status.HTTP_200_OK)
                
                else:
                    error_message = ocr_result.get('message', 'Unknown OCR error') if ocr_result else 'OCR processing failed'
                    logger.error(f"[{request_id}] OCR processing failed: {error_message}")
                    
                    return Response(
                        {
                            'success': False,
                            'message': 'OCR processing failed',
                            'error': error_message,
                            'processing_id': request_id,
                            'storage_info': {
                                'original_file': {
                                    'uploaded_to_gcs': storage_upload_result['success'] if storage_upload_result else False,
                                    'gcs_path': uploaded_file_path if storage_upload_result and storage_upload_result['success'] else None
                                }
                            }
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )
                    
            except Exception as e:
                logger.error(f"[{request_id}] Exception during OCR processing: {str(e)}", exc_info=True)
                return Response(
                    {
                        'success': False,
                        'message': 'Internal server error during OCR processing',
                        'error': str(e),
                        'processing_id': request_id
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            finally:
                # Clean up local temporary file if it was created
                if temp_file_path:
                    try:
                        if default_storage.exists(temp_file_path):
                            default_storage.delete(temp_file_path)
                            logger.debug(f"[{request_id}] Local temporary file cleaned up: {temp_file_path}")
                    except Exception as cleanup_error:
                        logger.warning(f"[{request_id}] Failed to cleanup local temporary file: {cleanup_error}")
        
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error in OCR pipeline: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Unexpected server error in OCR pipeline',
                    'error': str(e),
                    'processing_id': request_id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
