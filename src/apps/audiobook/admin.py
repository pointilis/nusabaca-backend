from django.contrib import admin
from .models import * # Import all models from the audiobook app

@admin.register(Recognition)
class RecognitionAdmin(admin.ModelAdmin):
    pass
