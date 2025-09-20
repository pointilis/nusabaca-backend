from django.urls import path
from .upload import views, async_views

urlpatterns = [
    # Synchronous upload (original)
    path("upload/", views.UploadAPIView.as_view(), name="upload"),
    
    # Asynchronous upload endpoints
    path("upload/async/", async_views.AsyncUploadAPIView.as_view(), name="async-upload"),
    path("upload/status/<str:task_id>/", async_views.TaskStatusAPIView.as_view(), name="task-status"),
    path("upload/tasks/", async_views.TaskListAPIView.as_view(), name="task-list"),
]
