import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nusabaca.settings.development')

app = Celery('nusabaca')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    # Broker settings
    broker_url=getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    
    # Task settings
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'apps.ocr.tasks.process_ocr_upload': {
            'queue': 'ocr_processing',
            'routing_key': 'ocr.process',
        },
        'apps.ocr.tasks.get_task_status': {
            'queue': 'status_check',
            'routing_key': 'status.check',
        }
    },
    
    # Task priorities
    task_default_priority=5,
    worker_disable_rate_limits=True,
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    return {'message': 'Celery is working!', 'task_id': self.request.id}