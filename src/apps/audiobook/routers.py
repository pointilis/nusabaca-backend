from django.urls import path, include
from .restful import routers

urlpatterns = [
    # RESTful API routes
    path('audiobook/', include((routers, 'audiobook'), namespace='audiobook')),
]
