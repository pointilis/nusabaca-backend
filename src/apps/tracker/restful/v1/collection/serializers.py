from rest_framework import serializers
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from apps.tracker.models import BiblioCollection
from apps.library.models import Biblio, Author, Genre, Publisher


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

    @transaction.atomic
    def create(self, validated_data):
        """Create a new BiblioCollection entry"""
        validated_data.update(self.defaults)
        instance = BiblioCollection.objects.create(**validated_data)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update an existing BiblioCollection entry"""
        print(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_internal_value(self, data):
        # create or get biblio
        biblio, created = self._handle_biblio(data)
        # create or get collection
        collection = self._handle_collection(data)
        data = super().to_internal_value(data)
        data.update({'biblio': biblio, 'collection': collection})
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        detail_url = reverse('api:tracker:v1:collection-detail', args=[instance.id])

        data['_detail_url'] = self.request.build_absolute_uri(detail_url)
        # Convert many-to-many relationships to name lists
        data['authors'] = [author.name for author in instance.authors.all()]
        data['genres'] = [genre.name for genre in instance.genres.all()]
        data['publishers'] = [publisher.name for publisher in instance.publishers.all()]
        return data

    def _handle_biblio(self, data):
        fields = Biblio._meta.fields
        biblio_data = {field.name: data.get(field.name) for field in fields if field.name in data}
        biblio, created = Biblio.objects.get_or_create(
            title=biblio_data.pop('title', None),
            isbn=biblio_data.pop('isbn', None),
            issn=biblio_data.pop('issn', None),
            defaults={
                'created_by': self.request.user,
                'modified_by': self.request.user,
                **biblio_data
            }
        )

        # Handle related fields if provided
        authors_data = data.get('authors', None)
        genres_data = data.get('genres', None)
        publishers_data = data.get('publishers', None)

        if authors_data:
            self._handle_authors(biblio, authors_data)
        if genres_data:
            self._handle_genres(biblio, genres_data)
        if publishers_data:
            self._handle_publishers(biblio, publishers_data)

        return biblio, created

    def _handle_collection(self, data):
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

    def _handle_authors(self, biblio, authors_data):
        """Handle author relationships"""
        if authors_data:
            # Clear existing relationships
            biblio.authors.clear()

            for author_name in authors_data:
                name = author_name.strip()
                author, created = Author.objects.get_or_create(
                    name=name,
                    defaults={
                        'content_object': biblio,
                        **self.defaults
                    }
                )
                biblio.authors.add(author)

    def _handle_genres(self, biblio, genres_data):
        """Handle genre relationships"""
        if genres_data:
            # Clear existing relationships
            biblio.genres.clear()
            
            for genre_name in genres_data:
                name = genre_name.strip()
                genre, created = Genre.objects.get_or_create(name=name, defaults=self.defaults)
                biblio.genres.add(genre)

    def _handle_publishers(self, biblio, publishers_data):
        """Handle publisher relationships"""
        if publishers_data:
            # Clear existing relationships
            biblio.publishers.clear()
            
            for publisher_name in publishers_data:
                name = publisher_name.strip()
                publisher, created = Publisher.objects.get_or_create(
                    name=name,
                    defaults={
                        **self.defaults,
                        'content_object': biblio
                    }
                )
                biblio.publishers.add(publisher)
