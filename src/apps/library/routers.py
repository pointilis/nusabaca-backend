from django.urls import path, include
from .restful import routers

urlpatterns = [
    # RESTful API routes
    path('library/', include((routers, 'library'), namespace='library')),
]
