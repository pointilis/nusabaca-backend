from django.urls import path, include
from .restful import routers

app_name = 'ocr'

urlpatterns = [
    # RESTful API routes
    path('api/', include(routers), name='ocr-api'),
]
