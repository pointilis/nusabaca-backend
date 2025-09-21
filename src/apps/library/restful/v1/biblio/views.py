from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response

from apps.library.models import Biblio
from .serializers import BiblioSerializer, BiblioCreateUpdateSerializer


class BiblioList(generics.ListCreateAPIView):
    """
    API view to list and create biblios.
    """
    queryset = Biblio.objects.all()
    serializer_class = BiblioCreateUpdateSerializer
