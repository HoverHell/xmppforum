""" Sample XMPP-related views which can be used as-is.

Also provides a custom login_required which autoregisters XMPP users when
needed.  """

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _

from .xmppbase import (XmppResponse, login_required,
  get_login_required_wrapper)
from .util import _set_user_jid

## XMPP registration/autoregistration stuff.
# ! XXX: Might need a global get_login_required_wrapper(xmpp_unreg_view)
#  setting.

def xmpp_register_cmd(request, nickname=None, password=None):
    """ Provides all necessary registration-related functionality for XMPP.
    XMPP-only view.  """
    if nickname is None:  # Allow registration w/o specifying nickname.
        nickname = request.srcjid
    # We're going to register one anyway.
    ruser, created = User.objects.get_or_create(username=nickname)
    if created:  # Okay, registered one.
        _set_user_jid(ruser, request.srcjid)
        if password is not None:
            ruser.set_password(password)
        ruser.save()
        # ! TODO: Ask user for a vcard. (set photosum to nothing and
        #  checkphoto with old?..)
        return XmppResponse(_("Registration successful."))
    else:
        # Note: check_password can be True if passord is None
        if (password is not None) and ruser.check_password(password):
            if request.user.is_authenticated():
                # ? What to do here, really?
                # ! XXX: Right now this prevents from authenticating into a
                #  different user from own JID.
                return XmppResponse(_("You are already registered"))
            else:  # 'authenticate into' an existing webuser.
                _set_user_jid(ruser, request.srcjid)
                return XmppResponse(_("JID setting updated successfully."))
        else:
            raise PermissionDenied, "Authentication to an existing user failed."
    # Optional: change state to 'password input' if no password
    # !! Possible problem if password (or, esp., both) contain spaces.


def xmpp_autoregister_user(request, function, *args, **kwargs):
    """ If XMPP user needs to be registered - try to register, and tell
    either way.  """
    jidname = request.srcjid.split('@')[0]
    if User.objects.filter(username__iexact=jidname).exists():
        return XmppResponse("You have to register to do this."
          "Additionally, username '%r' is unavailable so I could not "
          "autoregister you" % jidname)
    else:  # no such user - just autoregister him!
        # Use that view to actually register:
        regresp = xmpp_register_cmd(request, jidname)
        # ? do the initial command, too? Perhaps not.
        #return function(request, *args, **kwargs)
        return XmppResponse("You were just registered as '%s'. Please "
          "re-send the command to actually execute it." % jidname)

# This one is using more default login_required because autoregistering for
# this makes no sense.
@login_required
def xmpp_unregister_cmd(request):
    """ Disassociate (log off?) JID from the user.  """
    if not request.user.password:  # password is empty.
        # Deny unregistering since that would effectively disable the login.
        # Although, there are still ways to accidentally do that, like
        # logging in into another user from XMPP.
        return XmppResponse("You have no password set. Unregister would "
          "render the login inaccessible. Will not do that.")
    request.user.sb_usersettings.jid = None
    return XmppResponse("Goodbye, %r." % request.user.username) 


# Redefine the login_requred!
login_required = get_login_required_wrapper(xmpp_autoregister_user)


@login_required
def xmpp_web_login_cmd(request):
    """ Lets XMPP users log in into the web without using any password. 
    Uses the 'loginurl' django app.  """
    import loginurl.utils
    from django.core.urlresolvers import reverse
    current_site = Site.objects.get_current()
    key = loginurl.utils.create(request.user)
    url = u"http://%s%s" % (
      unicode(current_site.domain),
      reverse('loginurl_login', kwargs={'key': key.key}),
    )
    # * note that this reverse() requires quite a hack as of loginurl 0.1.3
    return XmppResponse('Login url: <a href="%s">%s</a> .' % (url, url))


@login_required
def xmpp_web_changepw(request, password=''):
    """ Change (or set) user's password for web login.  Can be empry
    (effectively disabling logging in with pasword).  """
    # JID is supposedly trusted and can *just* change it.
    request.user.set_password(password)
    if password:
        return XmppResponse("Password changed.")
    else:
        return XmppResponse("Password disabled.") 
