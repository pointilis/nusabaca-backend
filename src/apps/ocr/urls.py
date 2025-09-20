from django.urls import path, include
from .restful import routers

app_name = 'ocr'

urlpatterns = [
    # RESTful API routes
    path('ocr/', include((routers, 'ocr'), namespace='ocr')),
]
