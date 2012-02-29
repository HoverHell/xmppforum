"""
URLconf for registration and activation, using django-registration's
invitation backend.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from registration.views import activate, register

# Plugs into the default backend urls
urlpatterns = patterns('',
    url(r'^register/$',
        register,
        {'backend': 'registration_optionalemail.OptionalEmailBackend'},
        name='registration_register'),
    (r'', include('registration.backends.default.urls')),
)
