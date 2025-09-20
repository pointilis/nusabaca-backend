from .base import *  # noqa

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# Result settings - Using django-celery-results for database backend
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_TASK_RESULT_EXPIRES = 3600  # 1 hour
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_EXTENDED = True

# Django Celery Results configuration
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Celery Task Settings
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Task routing and execution
CELERY_TASK_ROUTES = {
    'apps.ocr.tasks.process_ocr_upload': {
        'queue': 'ocr_processing',
        'routing_key': 'ocr.process',
    },
    'apps.ocr.tasks.get_task_status': {
        'queue': 'status_check', 
        'routing_key': 'status.check',
    }
}

# Task execution settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task state and monitoring
CELERY_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes for workers
CELERY_TASK_CREATE_MISSING_QUEUES = True
