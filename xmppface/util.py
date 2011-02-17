""" Various utility functions for both internal and external use. Might get
moved (grouped) somewhere else.  """

# cmdresolver / urlresolver hack.
# ! XXX: Does not work well yet: url() at django.conf.urls.defaults uses
#  explicit RegexURLResolver for include()'d patterns.
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import RegexURLResolver


import logging
import traceback
_log = logging.getLogger('xmppfaceutil')


class RegexCmdResolver(RegexURLResolver):
    """ A small hack of RegexURLResolver for 'urlpatterns' -> 'cmdpatterns'
    rename. """
    
    def _get_url_patterns(self):
        patterns = getattr(self.urlconf_module, "cmdpatterns",
            self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            raise ImproperlyConfigured("The included cmdconf %s doesn't "
              " have any patterns in it" % self.urlconf_name)
        return patterns
    
    url_patterns = property(_get_url_patterns)


def _get_user_qs(jid):
    """ Attempts to find a User with the specified JID. Returns filter
    QuerySet. """
    from django.contrib.auth.models import User
    try:
        # ! XXX: This depends on snapboard-specific UserSettings model.
        # ? Add User ForeignKey to XmppContact?
        return User.objects.filter(sb_usersettings__jid__exact=jid)
    except Exception:  # FieldError?
        _log.error("_get_user_qs: Could not search for a User by JID!")
        _log.debug(traceback.format_exc())
        return []
def _set_user_jid(user, jid):
    """ Sets the user's JID.  XXX: Possibly temporary helper.  """
    from snapboard.models import UserSettings
    userset, cr = UserSettings.objects.get_or_create(user=user)
    userset.jid = jid  # ! FIXME: It should be unique.
    userset.save()


def _get_user_or_anon(jid):
    """ Returns a user with the specified JID or AnonymousUser if there's no
    such (registered) user.  """
    user_qs = _get_user_qs(jid)[:1]
    if user_qs:
        return user_qs[0]
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()
