from django.db import models
import uuid


# Create your models here.
class SNARequest(models.Model):
    idempotent_uuid = models.UUIDField(default= uuid.uuid4, editable=False, null=False, blank=False)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    data = models.JSONField(default=dict, null=True, blank=True)
    result = models.BooleanField(default=False, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    