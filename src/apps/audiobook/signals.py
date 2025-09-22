import logging

from celery.signals import task_success
from apps.audiobook.models import Recognition
from apps.ocr.tasks import submit_tts_task

# Configure logger
logger = logging.getLogger(__name__)


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    # Log the successful task execution
    name = sender.name if sender else None
    if name is not None and name == 'apps.ocr.tasks.process_ocr_upload':
        task_id = result.get('task_id', None)
        ocr_result = result.get('ocr_result', {})
        user_metadata = result.get('user_metadata', {})
        biblio = user_metadata.get('biblio') if user_metadata else None

        logger.info(f"Task signal received: {name} completed successfully, result: {biblio}")
        
        if biblio:
            biblio_id = biblio.get('id')
            page_number = biblio.get('page_number')

            try:
                full_text = ocr_result.get('full_text', '')
                language = ocr_result.get('language', 'en')

                # Update or create Recognition entry
                Recognition.objects.update_or_create(
                    biblio_id=biblio_id,
                    page_number=page_number,
                    defaults={
                        'full_text': full_text,
                        'language': language,
                        'result': ocr_result,
                        'task_id': task_id,
                    }
                )

                task_id = submit_tts_task(
                    text=full_text,
                    language_code=language,
                    voice_gender='female',
                    voice_index=0,
                    audio_format='mp3',
                    speaking_rate=0.85,
                )

                logger.info(f"task_id: {task_id}")

            except Exception as e:
                logger.error(f"Error updating Recognition for task id {task_id}: {e}")
