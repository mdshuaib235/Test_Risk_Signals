"""
URL configuration for src project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from core.views import (
    AppRegisterView,
    BankRegisterView,
    DeviceRebindView,
    DeviceRegisterView,
    DeviceRevokeView,
    DeviceValidateView,
    TestAPIView,
)

urlpatterns = [
    path("test", TestAPIView.as_view(), name="test_apiview"),
    path("bank/register/", BankRegisterView.as_view()),
    path("app/register/", AppRegisterView.as_view()),
    path("device/register/", DeviceRegisterView.as_view()),
    path("device/validate/risk/", DeviceValidateView.as_view()),
    path("device/rebind/", DeviceRebindView.as_view()),
    path("device/revoke/", DeviceRevokeView.as_view()),
]
