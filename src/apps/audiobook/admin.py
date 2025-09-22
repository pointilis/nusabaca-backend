from django.contrib import admin
from .models import * # Import all models from the audiobook app

@admin.register(PageFile)
class PageFileAdmin(admin.ModelAdmin):
    pass


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    pass
