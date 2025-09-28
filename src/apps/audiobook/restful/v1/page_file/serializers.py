import logging


from rest_framework import serializers
from django.db import transaction
from django.urls import reverse
from apps.audiobook.models import PageFile
from apps.ocr.tasks import submit_ocr_task
from ..audio_file.serializers import AudioFileSerializer

# Configure logger
logger = logging.getLogger(__name__)


class PageFileSerializer(serializers.ModelSerializer):
    audiofile = AudioFileSerializer(read_only=True, many=False)
    updated = serializers.BooleanField(read_only=True, default=False)
    created = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = PageFile
        fields = '__all__'
        extra_kwargs = {
            'language': {'read_only': False, 'required': True},
            'file_format': {'read_only': True},
            'full_text': {'read_only': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = self.context.get('request', None)

    @transaction.atomic
    def create(self, validated_data):
        logger.debug(f"Creating/Updating PageFile with data: {validated_data}")

        file = validated_data.pop('page_file', None)
        page_number = validated_data.pop('page_number', None)
        biblio = validated_data.pop('biblio_collection', None)
        language = validated_data.get('language', 'en')
        voice_gender = validated_data.get('voice_gender', 'male')

        # Create or update PageFile instance
        instance, created = self.Meta.model.objects.update_or_create(
            biblio_collection=biblio,
            page_number=page_number,
            defaults=validated_data
        )

        # Set task ID and initiate file processing
        task_id = self._file_processing(instance, file, language, voice_gender)
        instance.task_id = task_id
        instance.save()

        # Set created/updated flags
        setattr(instance, 'created', created)
        setattr(instance, 'updated', not created)

        logger.info(f"PageFile created/updated with ID: {instance.id}, Task ID: {task_id}")
        return instance
    
    @transaction.atomic
    def update(self, instance, validated_data):
        logger.debug(f"Updating PageFile ID: {instance.id}")

        file = validated_data.pop('page_file', None)
        language = validated_data.get('language', 'en')
        voice_gender = validated_data.get('voice_gender', 'male')

        # Update instance fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Set task ID and initiate file processing
        task_id = self._file_processing(instance, file, language, voice_gender)
        instance.task_id = task_id
        instance.save()

        # Set created/updated flags
        setattr(instance, 'created', False)
        setattr(instance, 'updated', True)

        logger.info(f"PageFile updated with ID: {instance.id}, Task ID: {task_id}")
        return instance

    def get_unique_together_validators(self):
        # Disable the unique together validator to allow custom handling
        return []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        processing_info = self._file_processing_info(instance.task_id)
        detail_url = reverse('api:audiobook:v1:page-file-detail', args=[instance.id])
        
        data.update({
            'processing_info': processing_info,
            'created': getattr(instance, 'created', False),
            'updated': getattr(instance, 'updated', False),
            '_detail_url': self.request.build_absolute_uri(detail_url)
        })
        
        return data

    def _file_processing(self, instance, file, language, voice_gender='male'):
        logger.debug(f"Starting file processing for PageFile ID: {instance.id}")
        
        # Read file data
        file.seek(0)
        file_data = file.read()
        file.seek(0)

        # Prepare user metadata
        user_metadata = {
            'user_ip': self.request.META.get('REMOTE_ADDR', 'unknown'),
            'user_agent': self.request.META.get('HTTP_USER_AGENT', 'unknown')[:200],  # Limit length
            'submitted_at': str(self.request.META.get('HTTP_DATE', '')),
            'voice_gender': voice_gender,
            'biblio_collection': {
                'id': str(instance.biblio_collection.id),
                'page_id': str(instance.id),
                'page_number': instance.page_number,
            },
        }

        # Submit task to Celery
        task_id = submit_ocr_task(
            file_data=file_data,
            filename=file.name,
            content_type=file.content_type or 'application/octet-stream',
            language=language,
            extract_format='structured',
            confidence_threshold=0.8,
            user_metadata=user_metadata,
            voice_gender=voice_gender
        )
        return task_id

    def _file_processing_info(self, task_id):
        # Placeholder for retrieving task result if needed
        status_url = reverse('api:ocr:v1:async-upload-status', args=[task_id])
        absolute_status_url = self.request.build_absolute_uri(status_url)
        return {
            'check_url': absolute_status_url,
            'recommended_interval_seconds': 5,
            'timeout_minutes': 30
        }
