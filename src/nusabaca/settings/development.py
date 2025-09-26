import os

from .base import * # noqa
from .celery_config import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['LAPTOP-D3O5RTCV.local', 'localhost', '127.0.0.1', '172.23.80.1', '192.168.1.5']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'nusabaca'),  # Your database name
        'USER': os.environ.get('DB_USER', 'postgres'),  # Your database user
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'),  # Your database user's password
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),  # Or your database server's IP/hostname
        'PORT': os.environ.get('DB_PORT', '5432'),  # Leave empty for default, or specify port if needed
    }
}
