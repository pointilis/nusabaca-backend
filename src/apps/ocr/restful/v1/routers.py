from django.urls import path
from .upload import views, async_views as upload_async_views
from .tts import async_views as tts_async_views

urlpatterns = [
    # Test task endpoint
    path("test-task/", views.TestTaskAPIView.as_view(), name="test-task"),

    # Synchronous upload (original)
    path("upload/", views.UploadAPIView.as_view(), name="upload"),
    
    # Asynchronous upload endpoints
    path("upload/async/", upload_async_views.AsyncUploadAPIView.as_view(), name="async-upload"),
    path("upload/status/<str:task_id>/", upload_async_views.TaskStatusAPIView.as_view(), name="async-upload-status"),
    path("upload/tasks/", upload_async_views.TaskListAPIView.as_view(), name="async-upload-task-list"),

    # Asynchronous TTS endpoints
    path("tts/async/", tts_async_views.AsyncTTSAPIView.as_view(), name="async-tts"),
    path("tts/status/<str:task_id>/", tts_async_views.TTSTaskStatusAPIView.as_view(), name="async-tts-status"),
    path("tts/tasks/", tts_async_views.TTSTaskListAPIView.as_view(), name="async-tts-task-list"),
]
