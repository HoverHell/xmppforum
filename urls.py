
from django.conf import settings
from django.contrib import admin
#from django.contrib.auth import views as auth_views

# default error handlers:
from django.conf.urls.defaults import (handler404, handler500,
  patterns, include)

admin.autodiscover()

# Address under the site root for forum main URLs.
# ? Move to settings?
#mainurl = 'xb/'
mainurl = ''

urlpatterns = patterns('',)  # start with empty for easier playing with ordering.


if mainurl:
    ## Redirect to home by default (if it's defined).
    urlpatterns += patterns('',
        (r'^$', 'django.views.generic.simple.redirect_to',
          {'url': '/%s' % mainurl}),
    )


## Auth
urlpatterns += patterns('',
    (r'^accounts/login/$', 'django.contrib.auth.views.login',
      {'template_name': 'snapboard/signin.html'}, 'auth_login'),
    (r'^accounts/logout/$', 'django.contrib.auth.views.logout',
      {'template_name': 'snapboard/signout.html'}, 'auth_logout'),
)


## Admin
urlpatterns += patterns('',
    (r'^admin/(.*)', admin.site.root),
)


import notification
urlpatterns += patterns('',
    # As long as we don't include django-notification's urlconf, we must define the URL for 
    # 'notification_notices' ourselves because of notification/models.py:251.
    #(r'^notices/', 'django.views.generic.simple.redirect_to', 
    #  {'url': '/snapboard/'}, 'notification_notices'),
    (r'^notices/', include('notification.urls')),
)


## Easy-set-up static
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


## loginurl
try:
    import loginurl.urls
except ImportError:
    pass
else:  # do our scary things!..
    pl1 = [rep for rep in loginurl.urls.urlpatterns if
      rep.callback == loginurl.urls.login]
    if pl1:  # force a proper name unto it.
        pl1[0].name = 'loginurl_login'
    urlpatterns += patterns('',
        (r'^loginurl/', include('loginurl.urls'), {}, 'loginurl'),
    )


## "home" - can be at the root.
urlpatterns += patterns('',
    (r'^%s' % mainurl, include('snapboard.urls')),
)
