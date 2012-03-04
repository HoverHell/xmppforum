
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


## Registration:
urlpatterns += patterns('',  ## XXX: No idea why this is needed.
    (r'^accounts/password/$', 'django.views.generic.simple.redirect_to',
       {'url': '/'}),
)

urlpatterns += patterns('', 
    ## XXX: Possibly temporary.  Users end up here after being redirected by
    ## registraton backend.  Until such page is implemented - redirect them
    ## somewhere else.
    (r'^users/', 'django.views.generic.simple.redirect_to',
       {'url': '/'}),
)

import snapboard.forms
try:  # XXX: django-registration < 0.8 backwards compatibility. 0.8+ part:
    import registration.backends
    urlpatterns += patterns('',
        (r'^accounts/', include('registration_optionalemail.urls')),
    )
except ImportError:  # pre-0.8
    urlpatterns += patterns('',
        (r'^accounts/register/$', 'registration.views.register', 
          {'form_class': snapboard.forms.RegistrationFormEmailFree,
           'template_name': 'registration/register.html',
           },
          'registration_register'),
        (r'^accounts/', include('registration.urls')),
    )

## Admin
urlpatterns += patterns('',
#    (r'^admin/(.*)', admin.site.root),
    (r'^admin/', include(admin.site.urls)),
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
if settings.SERVE_STATIC:
    urlpatterns += patterns('',
        (r'^m/(?P<path>.*)$',
          'django.views.static.serve',
          {'document_root': settings.MEDIA_ROOT}),
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
    ## (can just use `reverse('loginurl.urls.login', ...)`, though.
    _pl1 = [rep for rep in loginurl.urls.urlpatterns if
      rep.callback == loginurl.urls.login]
    if _pl1:  # force a proper name unto it.
        _pl1[0].name = 'loginurl_login'
    urlpatterns += patterns('',
        (r'^loginurl/', include('loginurl.urls'), {}, 'loginurl'),
    )


## XMPP over POST.
urlpatterns += patterns('',
    (r'', include('xmppface.urls')),
)

## "home" - can be at the root.
urlpatterns += patterns('',
    (r'^%s' % mainurl, include('snapboard.urls')),
)
