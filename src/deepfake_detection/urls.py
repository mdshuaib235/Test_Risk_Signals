from django.contrib import admin
from django.urls import include, path

from deepfake_detection.views import (
    UploadMediaAPIViews,
    DeepfakeStatusView,
    DemoUploadView,
    DemoResultPageView,
)

urlpatterns = [
    path("scan/", UploadMediaAPIViews.as_view(), name="deepfake_upload_apiview"),
    path("result/<str:task_uuid>/", DeepfakeStatusView.as_view(), name="deepfake_result_apiview"),
    # demo client
    path("demo/", DemoUploadView.as_view(), name="demo_upload"),
    path("demo/result/<uuid:task_uuid>/", DemoResultPageView.as_view(), name="deepfake_result_page"),


   
]
