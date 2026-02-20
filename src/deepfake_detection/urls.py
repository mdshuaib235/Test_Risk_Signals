from deepfake_detection.views import (
    DeepfakeStatusView,
    DemoResultPageView,
    DemoUploadView,
    SensityWebhook,
    UploadMediaAPIViews,
)
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("scan/", UploadMediaAPIViews.as_view(), name="deepfake_upload_apiview"),
    path(
        "result/<str:task_uuid>/",
        DeepfakeStatusView.as_view(),
        name="deepfake_result_apiview",
    ),
    # demo client
    path("demo/", DemoUploadView.as_view(), name="demo_upload"),
    path(
        "demo/result/<uuid:task_uuid>/",
        DemoResultPageView.as_view(),
        name="deepfake_result_page",
    ),
    #  use webhook instead of pooling
    path("webhook/register/", SensityWebhook.as_view(), name="sensity_webhook"),
]
