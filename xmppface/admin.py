
from .models import *
from django.contrib import admin

class XMPPContactAdmin(admin.ModelAdmin):
    model = XMPPContact
    list_display = ('remote', 'local', 'auth_to', 'auth_from', 'photosum')


admin.site.register(XMPPContact, XMPPContactAdmin)
