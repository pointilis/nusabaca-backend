from apps.tracker.models import ReadingProgress
from django.conf import settings


def update_reading_progress_from_session(sender, instance, created, **kwargs):
    """Update reading progress when a new reading session is created"""
    if created:
        progress, created = ReadingProgress.objects.get_or_create(
            user=instance.user,
            biblio=instance.biblio,
            defaults={
                'current_page': instance.end_page,
                'total_pages_read': instance.end_page,
                'started_at': instance.start_time,
                'last_read_at': instance.end_time or instance.start_time,
            }
        )
        
        if not created:
            # Update existing progress
            progress.current_page = max(progress.current_page, instance.end_page)
            progress.total_pages_read = max(progress.total_pages_read, instance.end_page)
            progress.last_read_at = instance.end_time or instance.start_time
            
            if progress.reading_status == 'not_started':
                progress.reading_status = 'reading'
                progress.started_at = progress.started_at or instance.start_time
            
            progress.save()


def insert_biblio_from_library_to_collection(sender, instance, created, **kwargs):
    """Automatically add new biblios to a default collection"""
    from apps.tracker.models import Collection, BiblioCollection

    created_by = instance.created_by
    if not created:
        created_by = instance.modified_by

    default_collection = created_by.created_tracker_collection.filter(is_default=True).first()
    if not default_collection:
        # Create a default collection if none exists
        name = getattr(settings, 'DEFAULT_COLLECTION_NAME', 'Reading List')
        default_collection, _ = Collection.objects.get_or_create(
            name=name,
            defaults={'created_by': created_by, 'is_default': True}
        )

    # Copy biblio to collection
    BiblioCollection.objects.get_or_create(
        title=instance.title,
        collection_id=default_collection.id,
        biblio_id=instance.id,
        defaults={'created_by': created_by}
    )

    default_collection.biblios.add(instance)
    default_collection.save()


def biblio_collection_save_handler(sender, instance, **kwargs):
    """Ensure biblio details are synced in the collection entry"""
    print("BiblioCollection save signal triggered")
