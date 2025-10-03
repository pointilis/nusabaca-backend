import logging

from celery.signals import task_success
from apps.audiobook.models import AudioFile, PageFile
from apps.ocr.tasks import submit_tts_streaming_task, submit_tts_task

# Configure logger
logger = logging.getLogger(__name__)


@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    # Log the successful task execution
    task_id = result.get('task_id', None)
    name = sender.name if sender else None
    user_metadata = result.get('user_metadata', {})
    biblio_collection = user_metadata.get('biblio_collection') if user_metadata else None
    voice_gender = user_metadata.get('voice_gender', 'male')
    page_id = user_metadata.get('page_id', None)
    storage_info = result.get('storage_info', {})
    gcs_path = storage_info.get('gcs_path', '')

    if name is not None:
        if name == 'apps.ocr.tasks.process_ocr_upload':
            ocr_result = result.get('ocr_result', {})
            logger.info(f"Task signal received: {name} completed successfully, result: {biblio_collection}")

            if biblio_collection:
                cid = biblio_collection.get('id')
                page_number = biblio_collection.get('page_number')

                try:
                    full_text = ocr_result.get('full_text', '')
                    language = ocr_result.get('language', 'en')

                    # Update or create PageFile entry
                    instance, created = PageFile.objects.update_or_create(
                        biblio_collection_id=cid,
                        page_number=page_number,
                        defaults={
                            'full_text': full_text,
                            'language': language,
                            'result': result,
                            'task_id': task_id,
                            'page_file': gcs_path,
                            'voice_gender': voice_gender,
                        }
                    )

                    logger.info(f"PageFile {'created' if created else 'updated'} with id: {instance.biblio_collection.title} Page: {page_number}")
   
                    # Submit task to Celery
                    # tts_task_id = submit_tts_task(
                    #     text=full_text,
                    #     language_code=language,
                    #     voice_gender=voice_gender,
                    #     speaking_rate=0.8,
                    #     user_metadata={
                    #         'page_id': str(instance.id),  # Insert page id into user metadata for TTS task
                    #         'biblio_collection': biblio_collection,
                    #         **user_metadata
                    #     }
                    # )

                    tts_task_id = submit_tts_streaming_task(
                        text=full_text,
                        language_code=language,
                        voice_gender=voice_gender,
                        speaking_rate=0.8,
                        volume_gain_db=16.0,  # Increase volume by 16 dB
                        user_metadata={
                            'page_id': str(instance.id),  # Insert page id into user metadata for TTS task
                            'biblio_collection': biblio_collection,
                            'voice_gender': voice_gender,
                            **user_metadata
                        }
                    )

                    logger.info(f"TTS task submitted with Task ID: {tts_task_id} for PageFile ID: {instance.id}")

                except Exception as e:
                    logger.error(f"Error updating PageFile for task id {task_id}: {e}")

        if name == 'apps.ocr.tasks.process_tts_generation' or name == 'apps.ocr.tasks.process_tts_streaming_generation':
            logger.info(f"TTS Task signal received: {name} completed successfully")
            logger.info(f"TTS User metadata: {user_metadata}")

            if biblio_collection:
                cid = biblio_collection.get('id')
                page_number = biblio_collection.get('page_number')
                audio_info = result.get('audio_info', {})
                duration_seconds = audio_info.get('duration_estimate', 0)
                file_size_bytes = audio_info.get('size', 0)
                file_format = audio_info.get('format', 'mp3')

                logger.info(f"TTS Task details - CID: {cid}, Page ID: {page_id}")
                logger.info(f"TTS Audio gcs path: {gcs_path}")

                try:
                    # Update or create AudioFile entry
                    instance, created = AudioFile.objects.update_or_create(
                        page_file_id=page_id,
                        biblio_collection_id=cid,
                        page_number=page_number,
                        defaults={
                            'file_size_bytes': file_size_bytes,
                            'duration_seconds': duration_seconds,
                            'file_format': file_format,
                            'result': result,
                            'task_id': task_id,
                            'audio_file': gcs_path,
                            'voice_gender': voice_gender,
                        }
                    )

                    logger.info(f"TTS {'created' if created else 'updated'} with id: {instance.biblio_collection.title} Page: {page_number}")

                except Exception as e:
                    logger.error(f"Error updating TTS for task id {task_id}: {e}")
