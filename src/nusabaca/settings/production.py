from .base import * # noqa
from .celery_config import *  # noqa

DEBUG = False

if not DEBUG:
    LOGGING['handlers']['console']['filters'] = ['require_debug_false']
    LOGGING['handlers']['console']['level'] = 'WARNING'
