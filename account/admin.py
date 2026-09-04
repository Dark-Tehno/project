from django.contrib import admin
from .models import DarkAccount, Device, Version, EmailConfirmation, PasswordReset, LoginHistory, Token

# Register your models here.
admin.site.register(DarkAccount)
admin.site.register(Device)
admin.site.register(Version)
admin.site.register(EmailConfirmation)
admin.site.register(PasswordReset)
admin.site.register(LoginHistory)
admin.site.register(Token)