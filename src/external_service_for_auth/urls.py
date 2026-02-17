from django.contrib import admin
from django.urls import include, path

from .views import TestNumberInsights,  VerifyCheckAPIView, VerifyStartAPIView

urlpatterns = [
    path("insights/<str:phone_number>" , TestNumberInsights.as_view(), name="test_number_insights"),

    path(
        "start/<str:number>",
        VerifyStartAPIView.as_view(),
        name="verify_start"
    ),
    path(
        "check/<str:number>/<str:code>",
        VerifyCheckAPIView.as_view(),
        name="verify_check"
    ),

   
]
