from .base import * # noqa

if not DEBUG:
    LOGGING['handlers']['console']['filters'] = ['require_debug_false']
    LOGGING['handlers']['console']['level'] = 'WARNING'
