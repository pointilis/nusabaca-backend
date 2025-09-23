from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.library.models import Biblio
from .serializers import BiblioCreateUpdateSerializer


class BiblioList(generics.ListCreateAPIView):
    """
    API view to list and create biblios.
    """
    queryset = Biblio.objects.all()
    serializer_class = BiblioCreateUpdateSerializer
    permission_classes = [IsAuthenticated]
