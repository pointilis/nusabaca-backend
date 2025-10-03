import logging

from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TTSSerializer
from apps.ocr.tasks import submit_tts_task, get_tts_task_status_sync

# Configure logger
logger = logging.getLogger(__name__)


class AsyncTTSAPIView(APIView):
    """
    API View for handling asynchronous text-to-speech processing.
    Returns immediately with task ID while TTS generation happens in background.
    """

    def post(self, request, *args, **kwargs) -> Response:
        """
        Handle POST request for asynchronous TTS processing.
        
        Returns immediately with task ID for background processing.
        
        Args:
            request: HTTP request object containing the text and TTS parameters
            
        Returns:
            Response: JSON response with task ID and status URL
        """
        logger.info(f"Starting async TTS processing from {request.META.get('REMOTE_ADDR', 'unknown')}")
        
        try:
            # Validate the TTS request data
            serializer = TTSSerializer(data=request.data)

            if not serializer.is_valid():
                logger.warning(f"TTS validation failed: {serializer.errors}")
                return Response(
                    {
                        'success': False,
                        'message': 'TTS request validation failed',
                        'errors': serializer.errors
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extract validated data
            validated_data = serializer.validated_data
            text = validated_data.get('text') or validated_data.get('full_text')
            language_code = validated_data.get('language', 'en')
            voice_gender = validated_data.get('voice_gender', 'female')
            voice_index = validated_data.get('voice_index', 0)
            audio_encoding = validated_data.get('audio_encoding', 'mp3')
            speaking_rate = validated_data.get('speaking_rate', 1.0)
            pitch = validated_data.get('pitch', 0.0)
            volume_gain_db = validated_data.get('volume_gain_db', 0.0)
            file_prefix = validated_data.get('file_prefix', 'tts_audio')
            
            # Biblio metadata
            biblio = validated_data.get('biblio')
            page_number = validated_data.get('page_number')
            
            logger.info(f"Submitting async TTS task for text length: {len(text)} characters")
            
            # Prepare user metadata
            user_metadata = {
                'user_ip': request.META.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
                'submitted_at': request.META.get('HTTP_DATE', ''),
                'text_length': len(text),
                'text_preview': text[:100] + '...' if len(text) > 100 else text
            }
            
            # Add biblio info if provided
            if biblio:
                user_metadata['biblio'] = {
                    'id': str(biblio.id),
                    'page_number': page_number
                }
            
            # Submit task to Celery
            task_id = submit_tts_task(
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
            
            # Build status check URLs
            status_url = reverse('api:ocr:v1:async-tts-status', args=[task_id])
            absolute_status_url = request.build_absolute_uri(status_url)

            response_data = {
                'success': True,
                'message': 'TTS request submitted successfully. Processing in background.',
                'task_id': task_id,
                'status': 'PENDING',
                'text_info': {
                    'length': len(text),
                    'preview': text[:100] + '...' if len(text) > 100 else text,
                    'language': language_code
                },
                'processing_options': {
                    'language_code': language_code,
                    'voice_gender': voice_gender,
                    'voice_index': voice_index,
                    'audio_encoding': audio_encoding,
                    'speaking_rate': speaking_rate,
                    'pitch': pitch,
                    'volume_gain_db': volume_gain_db,
                    'file_prefix': file_prefix
                },
                'status_url': absolute_status_url,
                'polling_instructions': {
                    'check_url': absolute_status_url,
                    'recommended_interval_seconds': 3,
                    'timeout_minutes': 10
                }
            }
            
            # Add biblio info to response if provided
            if biblio:
                response_data['biblio_info'] = {
                    'id': str(biblio.id),
                    'title': getattr(biblio, 'title', 'Unknown'),
                    'page_number': page_number
                }
            
            logger.info(f"Async TTS task submitted successfully: {task_id}")
            
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Unexpected error in async TTS view: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to submit TTS processing task',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TTSTaskStatusAPIView(APIView):
    """
    API View for checking the status of TTS processing tasks.
    """
    
    def get(self, request, task_id: str, *args, **kwargs) -> Response:
        """
        Get the current status of a TTS processing task.
        
        Args:
            request: HTTP request object
            task_id: Celery task ID
            
        Returns:
            Response: JSON response with task status and results
        """
        try:
            logger.debug(f"Checking TTS task status for: {task_id}")
            
            # Get task status
            task_status = get_tts_task_status_sync(task_id)
            
            if not task_status:
                return Response(
                    {
                        'success': False,
                        'message': 'TTS task not found',
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
                'modified_at': task_status.get('modified_at'),
            }
            
            # Add results if task is completed successfully
            if user_status == 'completed' and 'result' in task_status:
                result = task_status['result']
                response_data.update({
                    'processing_id': result.get('processing_id'),
                    'text_info': result.get('text_info', {}),
                    'audio_info': result.get('audio_info', {}),
                    'storage_info': result.get('storage_info', {}),
                    'processing_info': result.get('processing_info', {}),
                    'processing_completed_at': result.get('processing_info', {}).get('processed_at')
                })
                
                # Add download URLs if available
                storage_info = result.get('storage_info', {})
                if storage_info.get('file_url'):
                    response_data['download_url'] = storage_info['file_url']
                    response_data['download_expires_at'] = storage_info.get('signed_url_expires_at')
                
                # Add audio file information
                if storage_info.get('filename'):
                    response_data['audio_file'] = {
                        'filename': storage_info['filename'],
                        'format': result.get('audio_info', {}).get('format'),
                        'size': storage_info.get('file_size'),
                        'size_mb': result.get('audio_info', {}).get('size_mb'),
                        'duration_estimate': result.get('audio_info', {}).get('duration_estimate')
                    }
            
            # Add error details if task failed
            elif user_status == 'failed' and 'result' in task_status:
                result = task_status['result']
                response_data.update({
                    'error_details': result.get('error_details', {}),
                    'retry_count': result.get('retry_count', 0)
                })
                
                # Include text info for debugging if available
                if 'text_length' in result:
                    response_data['text_info'] = {
                        'length': result['text_length']
                    }
            
            # Add polling instructions for pending/processing tasks
            if user_status in ['pending', 'processing', 'retrying']:
                response_data['polling_instructions'] = {
                    'recommended_interval_seconds': 3,
                    'timeout_minutes': 10
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error checking TTS task status {task_id}: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to check TTS task status',
                    'error': str(e),
                    'task_id': task_id
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TTSTaskListAPIView(APIView):
    """
    API View for listing recent TTS processing tasks.
    """
    
    def get(self, request, *args, **kwargs) -> Response:
        """
        Get a list of recent TTS processing tasks.
        
        Returns:
            Response: JSON response with task list
        """
        try:
            # This would require implementing task history storage
            # For now, return a placeholder response
            return Response(
                {
                    'success': True,
                    'message': 'TTS task listing not yet implemented',
                    'tasks': [],
                    'count': 0,
                    'note': 'Task history storage needs to be implemented'
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error listing TTS tasks: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'message': 'Failed to list TTS tasks',
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
