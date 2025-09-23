from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(('nusabaca.routers', 'api'), namespace='api')),  # Include OCR app URLs

    # Even when using headless, the third-party provider endpoints are stil
    # needed for handling e.g. the OAuth handshake. The account views
    # can be disabled using `HEADLESS_ONLY = True`.
    path('accounts/', include('allauth.urls')),
]
