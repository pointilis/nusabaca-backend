from rest_framework import serializers
from apps.audiobook.models import AudioFile


class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['audio_file', 'duration_seconds', 'result']
