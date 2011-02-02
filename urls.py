
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views

# default error handlers:
from django.conf.urls.defaults import handler404, handler500, patterns, include

admin.autodiscover()

urlpatterns = patterns('',
    (r'^snapboard/', include('snapboard.urls')),
    (r'^accounts/login/$', auth_views.login, {'template_name': 'snapboard/signin.html'}, 'auth_login'),
    (r'^accounts/logout/$', auth_views.logout, {'template_name': 'snapboard/signout.html'}, 'auth_logout'),

    # admin:
    (r'^admin/(.*)', admin.site.root),
)

urlpatterns += patterns('',
    ## Redirect to snapboard home by default.
    (r'^$', 'django.views.generic.simple.redirect_to', {'url': '/snapboard'}),
)

import notification
urlpatterns += patterns('',
    # As long as we don't include django-notification's urlconf, we must define the URL for 
    # 'notification_notices' ourselves because of notification/models.py:251.
    #(r'^notices/', 'django.views.generic.simple.redirect_to', 
    #  {'url': '/snapboard/'}, 'notification_notices'),
    (r'^notices/', include('notification.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )

## Registration:
import snapboard.forms
#import registration.views
urlpatterns += patterns('',
    (r'^accounts/register/$', 'registration.views.register', 
      {"form_class": snapboard.forms.RegistrationFormEmailFree},
      'registration_register'),  # ! Maybe should be in snapboard.urls
    (r'^accounts/', include('registration.urls')),
)

## Avatar
urlpatterns += patterns('',
    (r'^avatar/', include('avatar.urls')),
)
