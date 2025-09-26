from django.contrib import admin
from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('', include('apps.ocr.routers')),  # Include OCR app URLs
    path('', include('apps.library.routers')),  # Include Library app URLs
    path('', include('apps.tracker.routers')),  # Include Tracker app URLs
    path('', include('apps.audiobook.routers')),  # Include Audiobook app URLs

    # Include the API endpoints:
    path('_allauth/', include('allauth.headless.urls')),

    # Simple jwt
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
