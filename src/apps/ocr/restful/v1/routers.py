from django.urls import path
from .upload import views

urlpatterns = [
    path("upload/", views.UploadAPIView.as_view(), name="upload"),
]
