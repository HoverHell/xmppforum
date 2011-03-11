""" The primary way to allow Anonymous is through anonymous_login_required,
which replaces auth.AnonymousUser with a valid common auth.User if it's set
up.  It also sets user.really_anonymous to True.

If it's not set up - returns the usual
django.contrib.auth.decorators.login_required wrapper.  """

from django.conf import settings

ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', None)

if ANONYMOUS_NAME:
    from django.contrib.auth.models import User
    ANONYMOUS_USER = User.objects.get(username=ANONYMOUS_NAME)
    def anonymous_login_required(function=None):
        """ Decorator to replace auth's AnonymousUser with an actual usable
        User for particular views.  Sets user.really_anonymous if replaced. 
        Configurable by ANONYMOUS_NAME in the settings.  """
        def anon_decorate(request, *args, **kwargs):
            """ Internal wrapper of anonymous_login_required.  """
            if request.user.is_authenticated():
                return function(request, *args, **kwargs)
            else:  # Use Anonymous! Just for this request, of course.
                request.user = ANONYMOUS_USER
                request.user.really_anonymous = True
                return function(request, *args, **kwargs)
        return anon_decorate  # ! XXX: return functools.wraps(...)?
else:
    from django.contrib.auth.decorators import login_required
    def anonymous_login_required(function=None):
        """ A dummy function which uses auth.login_required since no
        ANONYMOUS_USER is set up.  """
        return login_required(function)
