from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(('nusabaca.routers', 'api'), namespace='api')),  # Include OCR app URLs
]
