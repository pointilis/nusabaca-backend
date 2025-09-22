import logging

from celery.signals import task_success
from apps.audiobook.models import AudioFile, PageFile

# Configure logger
logger = logging.getLogger(__name__)


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    # Log the successful task execution
    task_id = result.get('task_id', None)
    name = sender.name if sender else None
    user_metadata = result.get('user_metadata', {})
    biblio = user_metadata.get('biblio') if user_metadata else None
    storage_info = result.get('storage_info', {})
    gcs_path = storage_info.get('gcs_path', '')

    if name is not None:
        if name == 'apps.ocr.tasks.process_ocr_upload':
            ocr_result = result.get('ocr_result', {})
            logger.info(f"Task signal received: {name} completed successfully, result: {biblio}")
            
            if biblio:
                biblio_id = biblio.get('id')
                page_number = biblio.get('page_number')

                try:
                    full_text = ocr_result.get('full_text', '')
                    language = ocr_result.get('language', 'en')

                    # Update or create PageFile entry
                    instance, created = PageFile.objects.update_or_create(
                        biblio_id=biblio_id,
                        page_number=page_number,
                        defaults={
                            'full_text': full_text,
                            'language': language,
                            'result': result,
                            'task_id': task_id,
                            'page_file': gcs_path,
                        }
                    )

                    logger.info(f"PageFile {'created' if created else 'updated'} with id: {instance.biblio.title} Page: {page_number}")

                except Exception as e:
                    logger.error(f"Error updating PageFile for task id {task_id}: {e}")

        if name == 'apps.ocr.tasks.process_tts_generation':
            logger.info(f"TTS Task signal received: {name} completed successfully, result: {result}")

            if biblio:
                biblio_id = biblio.get('id')
                page_number = biblio.get('page_number')
                audio_info = result.get('audio_info', {})
                duration_seconds = audio_info.get('duration_estimate', 0)
                file_size_bytes = audio_info.get('size', 0)
                file_format = audio_info.get('format', 'mp3')

                try:
                    # Update or create AudioFile entry
                    instance, created = AudioFile.objects.update_or_create(
                        biblio_id=biblio_id,
                        page_number=page_number,
                        defaults={
                            'file_size_bytes': file_size_bytes,
                            'duration_seconds': duration_seconds,
                            'file_format': file_format,
                            'result': result,
                            'task_id': task_id,
                            'audio_file': gcs_path,
                        }
                    )

                    logger.info(f"TTS {'created' if created else 'updated'} with id: {instance.biblio.title} Page: {page_number}")

                except Exception as e:
                    logger.error(f"Error updating TTS for task id {task_id}: {e}")
