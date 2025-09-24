from django.contrib import admin
from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('', include('apps.ocr.routers')),  # Include OCR app URLs
    path('', include('apps.library.routers')),  # Include Library app URLs
    path('', include('apps.tracker.routers')),  # Include Tracker app URLs

    # Include the API endpoints:
    path('_allauth/', include('allauth.headless.urls')),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
