from django.contrib import admin
from django.urls import include, path

from deepfake_detection.views import (
    UploadMediaAPIViews,
    DeepfakeStatusView
)

urlpatterns = [
    path("test_vonage_number_insights/", TestNumberInsights.as_view(), name="deepfake_upload_apiview"),
    
   
]
