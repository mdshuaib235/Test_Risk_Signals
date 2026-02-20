from core.views import (
    AppRegisterView,
    BankRegisterView,
    DeviceRebindView,
    DeviceRegisterView,
    DeviceRevokeView,
    DeviceValidateView,
    TestAPIView,
)
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("test", TestAPIView.as_view(), name="test_apiview"),
    path("bank/register/", BankRegisterView.as_view()),
    path("app/register/", AppRegisterView.as_view()),
    path("device/register/", DeviceRegisterView.as_view()),
    path("device/validate/risk/", DeviceValidateView.as_view()),
    path("device/rebind/", DeviceRebindView.as_view()),
    path("device/revoke/", DeviceRevokeView.as_view()),
]
