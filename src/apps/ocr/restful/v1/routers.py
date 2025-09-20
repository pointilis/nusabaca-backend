from django.urls import path
from .upload import views, async_views

urlpatterns = [
    # Test task endpoint
    path("test-task/", views.TestTaskAPIView.as_view(), name="test-task"),

    # Synchronous upload (original)
    path("upload/", views.UploadAPIView.as_view(), name="upload"),
    
    # Asynchronous upload endpoints
    path("upload/async/", async_views.AsyncUploadAPIView.as_view(), name="async-upload"),
    path("upload/status/<str:task_id>/", async_views.TaskStatusAPIView.as_view(), name="async-upload-status"),
    path("upload/tasks/", async_views.TaskListAPIView.as_view(), name="async-upload-task-list"),
]
