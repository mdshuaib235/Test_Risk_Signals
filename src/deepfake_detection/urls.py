from django.contrib import admin
from django.urls import include, path

from deepfake_detection.views import (
    UploadMediaAPIViews,
    DeepfakeStatusView
)

urlpatterns = [
    path("scan/", UploadMediaAPIViews.as_view(), name="deepfake_upload_apiview"),
    path("result/<str:task_uuid>/", DeepfakeStatusView.as_view(), name="deepfake_result_apiview"),
   
]
