from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from apps.tracker.models import BiblioCollection
from .serializers import BiblioCollectionSerializer


class BiblioCollectionListCreateAPIView(generics.ListCreateAPIView):
    """
    API view to list and create BiblioCollection entries.
    """
    queryset = BiblioCollection.objects.all()
    serializer_class = BiblioCollectionSerializer
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['collection', 'biblio', 'created_by']
    search_fields = ['biblio__title', 'collection__name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default ordering
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return BiblioCollection.objects.filter(collection__created_by__id=user.id)


class CollectionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve details of a specific Collection.
    """
    queryset = BiblioCollection.objects.all()
    serializer_class = BiblioCollectionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'uuid'
