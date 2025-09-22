from django.apps import AppConfig


class OcrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ocr'
    label = 'ocr'
    verbose_name = 'OCR Application'

    def ready(self):
        import apps.ocr.signals  # noqa