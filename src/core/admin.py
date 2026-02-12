from django.contrib import admin

from .models import AuthLog, Bank, RegisteredApp, RequestNonce, UserDevice

admin.site.register(Bank)
admin.site.register(UserDevice)
admin.site.register(AuthLog)
admin.site.register(RequestNonce)
admin.site.register(RegisteredApp)
