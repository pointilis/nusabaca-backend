from apps.tracker.models import ReadingProgress


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
