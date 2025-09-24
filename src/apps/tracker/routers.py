from django.urls import path, include
from .restful import routers

urlpatterns = [
    # RESTful API routes
    path('tracker/', include((routers, 'tracker'), namespace='tracker')),
]
