from apps.tracker.models import Collection
from django.conf import settings


def user_saved(sender, instance, created, **kwargs):
    """Signal to handle actions after a user is created or updated"""
    if created:
        print(f"New user created: {instance.username}")

        # Create a default collection for the new user
        name = getattr(settings, 'DEFAULT_COLLECTION_NAME', 'Reading List')
        Collection.objects.get_or_create(
            created_by=instance,
            name=name,
            defaults={
                'description': 'This is your default collection.',
                'is_default': True,
                'is_public': False,
            }
        )
    else:
        print(f"User updated: {instance.username}")
