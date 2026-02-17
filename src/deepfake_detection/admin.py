from django.contrib import admin

# Register your models here.
from .models import DeepfakeTask, ServiceProvider

# TODO: update default UI
admin.site.register(ServiceProvider)
admin.site.register(DeepfakeTask)
