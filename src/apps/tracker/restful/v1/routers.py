from django.urls import path
from .collection.views import BiblioCollectionListCreateAPIView, CollectionDetailAPIView

urlpatterns = [
    path('collections/', BiblioCollectionListCreateAPIView.as_view(), name='collection-list'),
    path('collections/<uuid:uuid>/', CollectionDetailAPIView.as_view(), name='collection-detail'),
]
