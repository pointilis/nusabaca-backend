from rest_framework import serializers
from django.urls import reverse
from django.conf import settings
from apps.tracker.models import BiblioCollection
from apps.library.models import Biblio


class BiblioCollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for BiblioCollection model.
    Includes nested representation of the related Biblio.
    """
    class Meta:
        model = BiblioCollection
        fields = '__all__'
        read_only_fields = [
            'id', 'created_by', 'modified_by', 
            'created_at', 'modified_at'
        ]
        extra_kwargs = {
            'collection': {'required': False},
            'biblio': {'required': False},
            'publication_year': {'required': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.defaults = dict()
        self.request = self.context.get('request', None)

        if (self.request) and self.request.user.is_authenticated:
            self.defaults['created_by'] = self.request.user

    def create(self, validated_data):
        """Create a new BiblioCollection entry"""
        validated_data.update(self.defaults)
        instance = BiblioCollection.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        """Update an existing BiblioCollection entry"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_internal_value(self, data):
        biblio, created = self._biblio_handler(data)
        collection = self._collection_handler(data)
        data = super().to_internal_value(data)
        data.update({'biblio': biblio, 'collection': collection})
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        detail_url = reverse('api:tracker:v1:collection-detail', args=[instance.id])

        data['_detail_url'] = self.request.build_absolute_uri(detail_url)
        return data

    def _biblio_handler(self, data):
        fields = Biblio._meta.fields
        biblio_data = {field.name: data.get(field.name) for field in fields if field.name in data}
        biblio, created = Biblio.objects.get_or_create(
            title=biblio_data.pop('title', None),
            isbn=biblio_data.pop('isbn', None),
            issn=biblio_data.pop('issn', None),
            defaults={**biblio_data}
        )

        if created:
            biblio.created_by = self.request.user
            biblio.modified_by = self.request.user
        else:
            biblio.modified_by = self.request.user

        biblio.save()
        return biblio, created

    def _collection_handler(self, data):
        from apps.tracker.models import Collection
        collection_id = data.get('collection')
        if collection_id:
            try:
                collection = Collection.objects.get(id=collection_id)
                return collection
            except Collection.DoesNotExist:
                raise serializers.ValidationError(f"Collection with id {collection_id} does not exist.")
        
        collection, _ = Collection.objects.get_or_create(
            name=settings.DEFAULT_COLLECTION_NAME,
            defaults={'created_by': self.request.user, 'modified_by': self.request.user, 'is_default': True}
        )
    
        return collection
