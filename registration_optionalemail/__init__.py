from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site

from registration import signals
from registration.backends.default import DefaultBackend
from registration.backends.simple import SimpleBackend
from registration_optionalemail.forms import RegistrationFormEmailFree
from registration.models import RegistrationProfile


class OptionalEmailBackend(DefaultBackend):
    """ Backend that allows registration without providing an e-mail
    (combination of default and simple backends).  """

    def register(self, request, **kwargs):
        """
        Given a username, email address and password, register a new user
        account, which will initially be inactive if the e-mail address is
        not empty.
        
        See registration.backends.default.DefaultBackend for further
        details.
        """
        username, email, password = kwargs['username'], kwargs['email'], \
            kwargs['password1']
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)
        if email:  # if it's not empty
            # Plug-plug-plug.
            return DefaultBackend.register(self, request, **kwargs)
        else:
            return SimpleBackend.register(self, request, **kwargs)

    def get_form_class(self, request):
        """ Return the default form class used for user registration. """
        return RegistrationFormEmailFree

    def post_registration_redirect(self, request, user):
        """ After registration, redirect to the user's account page. """
        return (user.get_absolute_url(), (), {})
