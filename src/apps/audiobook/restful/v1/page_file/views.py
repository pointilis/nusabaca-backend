import django_filters
from rest_framework import generics, filters
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsOwnerOrReadOnly
from apps.audiobook.models import PageFile
from .serializers import PageFileSerializer


class PageFileListCreateAPIView(generics.ListCreateAPIView):
    queryset = PageFile.objects.all()
    parser_classes = (MultiPartParser, )
    permission_classes = (IsAuthenticated, IsOwnerOrReadOnly, )
    serializer_class = PageFileSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'uuid'
    ordering = ['-page_number']
    ordering_fields = ['page_number']
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['biblio_collection']
    search_fields = ['biblio__title']

    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)
