from rest_framework import serializers
from apps.library.models import Biblio, Author, Genre, Publisher


class BiblioCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating biblios.
    Handles author, genre, and publisher relationships.
    """
    authors = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of author names",
        write_only=True
    )
    genres = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="List of genre names",
        write_only=True
    )
    publishers = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of publisher names",
        write_only=True
    )

    class Meta:
        model = Biblio
        fields = [
            'id', 'title', 'isbn', 'issn', 'original_title', 
            'description', 'original_publication_date', 'language',
            'authors', 'genres', 'publishers', 'total_pages', 'file_format',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.defaults = dict()
        self.request = self.context.get('request', None)

        if (self.request) and self.request.user.is_authenticated:
            self.defaults['created_by'] = self.request.user

    def create(self, validated_data):
        """Create a new biblio with related objects"""
        title = validated_data.pop('title')
        isbn = validated_data.get('isbn', None)
        issn = validated_data.get('issn', None)
        authors_data = validated_data.pop('authors', [])
        genres_data = validated_data.pop('genres', [])
        publishers_data = validated_data.pop('publishers', [])
        
        # Create or update the biblio
        biblio, created = Biblio.objects.update_or_create(
            title=title,
            isbn=isbn,
            issn=issn,
            defaults=validated_data
        )

        # Handle relationships
        self._handle_authors(biblio, authors_data)
        self._handle_genres(biblio, genres_data)
        self._handle_publishers(biblio, publishers_data)
        
        return biblio

    def update(self, instance, validated_data):
        """Update existing biblio with related objects"""
        authors_data = validated_data.pop('authors', None)
        genres_data = validated_data.pop('genres', None)
        publishers_data = validated_data.pop('publishers', None)
        
        # Update biblio fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update relationships if provided
        if authors_data is not None:
            self._handle_authors(instance, authors_data)
        if genres_data is not None:
            self._handle_genres(instance, genres_data)
        if publishers_data is not None:
            self._handle_publishers(instance, publishers_data)
        
        return instance

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

    def to_representation(self, instance):
        """Custom representation to include related object names"""
        data = super().to_representation(instance)
        
        # Convert many-to-many relationships to name lists
        data['authors'] = [author.name for author in instance.authors.all()]
        data['genres'] = [genre.name for genre in instance.genres.all()]
        data['publishers'] = [publisher.name for publisher in instance.publishers.all()]
        
        return data


class BiblioSerializer(serializers.ModelSerializer):
    """Simple biblio serializer for read operations"""
    authors = serializers.SerializerMethodField()
    genres = serializers.SerializerMethodField()
    publishers = serializers.SerializerMethodField()

    class Meta:
        model = Biblio
        fields = [
            'id', 'title', 'isbn', 'issn', 'original_title', 
            'description', 'original_publication_date', 'language',
            'authors', 'genres', 'publishers', 'created_at', 'updated_at'
        ]

    def get_authors(self, obj):
        return [author.name for author in obj.authors.all()]

    def get_genres(self, obj):
        return [genre.name for genre in obj.genres.all()]

    def get_publishers(self, obj):
        return [publisher.name for publisher in obj.publishers.all()]
