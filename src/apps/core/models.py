import uuid

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseModel(models.Model):
    """
    Abstract base model providing common fields for all library models:
    - UUID primary key
    - Timestamp fields (created_at, modified_at)
    - Authoring fields (created_by, modified_by)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_%(app_label)s_%(class)s'
    )
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_%(app_label)s_%(class)s'
    )
    
    class Meta:
        abstract = True
