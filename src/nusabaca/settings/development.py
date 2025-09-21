from .base import * # noqa
from .celery_config import *  # noqa

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nusabaca',  # Your database name
        'USER': 'postgres',  # Your database user
        'PASSWORD': '123456',  # Your database user's password
        'HOST': '127.0.0.1',  # Or your database server's IP/hostname
        'PORT': '5432',  # Leave empty for default, or specify port if needed
    }
}