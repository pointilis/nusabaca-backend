import logging

from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import FileSerializer
from apps.ocr.tasks import submit_ocr_task, get_ocr_task_status

# Configure logger
logger = logging.getLogger(__name__)


class AsyncUploadAPIView(APIView):
    """
    API View for handling asynchronous file uploads and OCR processing.
    Returns immediately with task ID while processing happens in background.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs) -> Response:
        """
        Handle POST request for asynchronous file upload and OCR processing.
        
        Returns immediately with task ID for background processing.
        
        Args:
            request: HTTP request object containing the uploaded file
            
        Returns:
            Response: JSON response with task ID and status URL
        """
        logger.info(f"Starting async OCR upload from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        try:
            # Validate the uploaded file
            file_serializer = FileSerializer(data=request.data)

            if not file_serializer.is_valid():
                logger.warning(f"File validation failed: {file_serializer.errors}")
                return Response(
                    {
                        'success': False,
                        'message': 'File validation failed',
                        'errors': file_serializer.errors
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = file_serializer.validated_data['file']
            language = file_serializer.validated_data.get('language', 'en')
            extract_format = file_serializer.validated_data.get('extract_format', 'text')
            confidence_threshold = file_serializer.validated_data.get('confidence_threshold', 0.8)
            
            # Biblio datasheet
            biblio = file_serializer.validated_data.get('biblio', None)
            page_number = file_serializer.validated_data.get('page_number', None)
            biblio_info = {
                'id': str(biblio.id) if biblio else None,
                'page_number': page_number if page_number else None
            }
            
            logger.info(f"Submitting async OCR task for file: {file.name} ({file.size} bytes)")
            
            # Read file data
            file.seek(0)
            file_data = file.read()
            file.seek(0)
            
            # Prepare user metadata
            user_metadata = {
                'user_ip': request.META.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],  # Limit length
                'submitted_at': str(request.META.get('HTTP_DATE', '')),
                'biblio': biblio_info,
            }
            
            # Submit task to Celery
            task_id = submit_ocr_task(
                file_data=file_data,
                filename=file.name,
                content_type=file.content_type or 'application/octet-stream',
                language=language,
                extract_format=extract_format,
                confidence_threshold=confidence_threshold,
                user_metadata=user_metadata
            )
            
            # Build status check URLs
            status_url = reverse('api:ocr:v1:async-upload-status', args=[task_id])
            absolute_status_url = request.build_absolute_uri(status_url)

            response_data = {
                'success': True,
                'message': 'File uploaded successfully. Processing in background.',
                'task_id': task_id,
                'status': 'PENDING',
                'file_info': file_serializer.get_file_info(),
                'processing_options': {
                    'language': language,
                    'extract_format': extract_format,
                    'confidence_threshold': confidence_threshold
                },
                'status_url': absolute_status_url,
                'polling_instructions': {
                    'check_url': absolute_status_url,
                    'recommended_interval_seconds': 5,
                    'timeout_minutes': 30
                }
            }
            
            logger.info(f"Async OCR task submitted successfully: {task_id}")
            
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Unexpected error in async upload view: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to submit processing task',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskStatusAPIView(APIView):
    """
    API View for checking the status of OCR processing tasks.
    """
    
    def get(self, request, task_id: str, *args, **kwargs) -> Response:
        """
        Get the current status of an OCR processing task.
        
        Args:
            request: HTTP request object
            task_id: Celery task ID
            
        Returns:
            Response: JSON response with task status and results
        """
        try:
            logger.debug(f"Checking status for task: {task_id}")
            
            # Get task status
            task_status = get_ocr_task_status(task_id)
            
            if not task_status:
                return Response(
                    {
                        'success': False,
                        'message': 'Task not found',
                        'task_id': task_id
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Map Celery states to user-friendly status
            status_mapping = {
                'PENDING': 'pending',
                'PROCESSING': 'processing', 
                'SUCCESS': 'completed',
                'FAILURE': 'failed',
                'RETRY': 'retrying',
                'REVOKED': 'cancelled'
            }
            
            user_status = status_mapping.get(task_status['status'], task_status['status'].lower())
            
            response_data = {
                'success': True,
                'task_id': task_id,
                'status': user_status,
                'progress': task_status.get('progress', 0),
                'message': task_status.get('message', ''),
                'updated_at': task_status.get('updated_at'),
            }
            
            # Add results if task is completed successfully
            if user_status == 'completed' and 'result' in task_status:
                result = task_status['result']
                response_data.update({
                    'processing_id': result.get('processing_id'),
                    'file_info': result.get('file_info', {}),
                    'storage_info': result.get('storage_info', {}),
                    'ocr_result': result.get('ocr_result', {}),
                    'processing_completed_at': result.get('processing_completed_at')
                })
                
                # Add download URLs if available
                storage_info = result.get('storage_info', {})
                if storage_info.get('original_file', {}).get('signed_url'):
                    response_data['download_urls'] = {
                        'original_file': storage_info['original_file']['signed_url'],
                        'results_file': storage_info.get('results_file', {}).get('signed_url')
                    }
            
            # Add error details if task failed
            elif user_status == 'failed' and 'result' in task_status:
                result = task_status['result']
                response_data.update({
                    'error_details': result.get('error_details', {}),
                    'retry_count': result.get('retry_count', 0)
                })
            
            # Add polling instructions for pending/processing tasks
            if user_status in ['pending', 'processing', 'retrying']:
                response_data['polling_instructions'] = {
                    'recommended_interval_seconds': 5,
                    'timeout_minutes': 30
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking task status {task_id}: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to check task status',
                    'error': str(e),
                    'task_id': task_id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskListAPIView(APIView):
    """
    API View for listing recent OCR processing tasks.
    """
    
    def get(self, request, *args, **kwargs) -> Response:
        """
        Get a list of recent OCR processing tasks.
        
        Returns:
            Response: JSON response with task list
        """
        try:
            # This would require implementing task history storage
            # For now, return a placeholder response
            return Response(
                {
                    'success': True,
                    'message': 'Task listing not yet implemented',
                    'tasks': [],
                    'count': 0
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error listing tasks: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to list tasks',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
