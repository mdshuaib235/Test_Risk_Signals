from django.contrib import admin

# Register your models here.
from .models import ServiceProvider, DeepfakeTask

# TODO: update default UI
admin.site.register(ServiceProvider)
admin.site.register(DeepfakeTask)