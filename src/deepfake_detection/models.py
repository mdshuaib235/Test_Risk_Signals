from django.db import models
import uuid

# Create your models here.

class ServiceProviderChoices(models.TextChoices):
    SENSITY = "SENSITY", "Sensity"
    OTHER = "OTHER", "Other"

class SensityTaskChoices(models.TextChoices):
    face_manipulation = "face_manipulation", "face_manipulation"
    ai_generated_image_detection = "ai_generated_image_detection" , "ai_generated_image_detection"
    voice_analysis = "voice_analysis", "voice_analysis"
    forensic_analysis = 'forensic_analysis', 'forensic_analysis'
    other = "other", "other"


class ServiceProvider(models.Model):
    name = models.CharField(
        max_length=55,
        choices=ServiceProviderChoices.choices,
        default=ServiceProviderChoices.SENSITY,
    )
    token = models.CharField(max_length=555, null=False, blank=False)
    is_active = models.BooleanField(default=True, null=True, blank=True)


class DeepfakeTask(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    provider = models.ForeignKey(
        "deepfake_detection.ServiceProvider",
        on_delete=models.CASCADE
    )

    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    media_file = models.FileField(upload_to="uploads/", null=True, blank=True)
    media_url = models.URLField(null=True, blank=True)

    request_payload = models.JSONField(null=True, blank=True)
    report_ids = models.JSONField(null=True, blank=True)
    response_full = models.JSONField(null=True, blank=True) 
    #  result

    status = models.CharField(max_length=50, default="created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DeepfakeTaskID: {self.id}"