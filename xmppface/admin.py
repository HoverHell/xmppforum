
from .models import *
from django.contrib import admin

# Experimental scary stuff:
def makefulladmin(targetmodel, pk=True, **kwa):
    """ Automatically generates and sets a ModelAdmin for the supplied
    model, listing all availble fields (skipping primary keys if pk=False). 
    """
    class SomeFullAdmin(admin.ModelAdmin):
        """ Helper class for `makefulladmin`.  """
        model = targetmodel
        list_display = [field.name for field in targetmodel._meta.fields
          if ((not field.primary_key) or pk)]
    for k, v in kwa.iteritems():
        setattr(SomeFullAdmin, k, v)
    admin.site.register(targetmodel, SomeFullAdmin)


for tmodel in (XMPPContact, UserSettings):
    makefulladmin(tmodel, pk=False)

#class XMPPContactAdmin(admin.ModelAdmin):
#    model = XMPPContact
#    #list_display = ('remote', 'local', 'auth_to', 'auth_from', 'photosum')
#    list_display = [f.name for f in XMPPContact._meta.fields]
#admin.site.register(XMPPContact, XMPPContactAdmin)
#class UserSettingsAdmin(admin.ModelAdmin):
#    model = UserSettings
#admin.site.register(UserSettings, UserSettingsAdmin)
