""" Various utility functions for both internal and external use. Might get
moved (grouped) somewhere else.  """

# cmdresolver / urlresolver hack.
# ! XXX: Does not work well yet: url() at django.conf.urls.defaults uses
#  explicit RegexURLResolver for include()'d patterns.

import logging
import traceback
_log = logging.getLogger('xmppfaceutil')


from django.core.urlresolvers import RegexURLResolver
from django.core.exceptions import ImproperlyConfigured
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


def get_user_qs(jid):
    """ Attempts to find a User with the specified JID. Returns filter
    QuerySet. """
    from django.contrib.auth.models import User
    try:
        return User.objects.filter(xf_usersettings__jid__exact=jid)
    except Exception:  # FieldError?
        _log.error("get_user_qs: Could not search for a User by JID!")
        _log.debug(traceback.format_exc())
        return []


from django.core.exceptions import ObjectDoesNotExist
def get_user_jid(user):
    try:
        return user.xf_usersettings.jid
    except Exception:  # ObjectDoesNotExist:
        return None


from .models import UserSettings
def set_user_jid(user, jid, forcenew=False):
    """ Sets the user's JID.  """
    userset = get_user_xfsettings(user)  # make them if needed.
    # Uniqueness:
    if jid:  # if not empty
        jqs = UserSettings.objects.filter(jid=jid)
        if jqs.exists():  # such JID already present.
            if forcenew:
                jqs.update(jid=jid)
            else:  # Deny changing.
                return  # ? XXX: throw up?
    # Set new.
    UserSettings.objects.filter(user=user).update(jid=jid)


DEFAULT_USER_XFSETTINGS = UserSettings()
def get_user_xfsettings(user):
    """ Return xmppface UserSettings for the specified user.  Creates them
    if there's none.  """
    # Similar to get_user_settings in snapboard(xmppboard).models
    if not user or not user.is_authenticated():
        return DEFAULT_USER_XFSETTINGS
    else:
        userset, cr = UserSettings.objects.get_or_create(user=user)
    return userset


def get_user_or_anon(jid):
    """ Returns a user with the specified JID or AnonymousUser if there's no
    such (registered) user.  """
    user_qs = get_user_qs(jid)[:1]
    if user_qs:
        return user_qs[0]
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()

