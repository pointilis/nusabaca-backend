import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nusabaca.settings.development')

app = Celery('nusabaca')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# This will automatically load all CELERY_* settings from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
    return {'message': 'Celery is working!', 'task_id': self.request.id}
