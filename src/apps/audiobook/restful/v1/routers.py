from django.urls import path
from .page_file import views as page_file_views

urlpatterns = [
    path("pages/", page_file_views.PageFileListCreateAPIView.as_view(), name="page-file-list"),
    path("pages/<uuid:uuid>/", page_file_views.PageFileDetailAPIView.as_view(), name="page-file-detail"),
]
