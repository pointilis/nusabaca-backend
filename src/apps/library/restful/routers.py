from django.urls import path, include

from .v1 import routers as v1_routers

urlpatterns = [
    path('v1/', include((v1_routers, 'v1'), namespace='v1')),
]
