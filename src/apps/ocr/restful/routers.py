from django.urls import path, include
from .v1 import routers

urlpatterns = [
    # API v1 routes
    path('v1/', include((routers, 'v1'), namespace='v1')),
]
