""" django-xmppface specific database models.

Note that django-xmppface also actively uses key-value cache storage if it
is provided in the django (see CACHE_BACKEND setting and django.core.cache). 
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User

__all__ = [
    'XMPPContact',
    'UserJID'
    ]

class XMPPContact(models.Model):
    """ Contains authentication status and some extra info for all known
    XMPP contacts.  """
    # Length is increased to reduce chance of problems with *very* long JIDs.
    remote = models.EmailField(max_length=100,
      verbose_name=_('remote jid'))
    local = models.EmailField(max_length=85, 
      verbose_name=_('local jid'))
    # Determines if bot has subsctiption to this contact.
    auth_to = models.BooleanField(default=False, 
      verbose_name=_('subscribed to'))
    # ...and if the contact is subscribed to bot's (local) jid.
    # ? In which case it can really be 'false', actually?
    auth_from = models.BooleanField(default=False,
      verbose_name=_('subscribed from'))
    # Status type: online / chat / away / xa / dnd / unavail.
    # It is preferrable to keep such volatile data in keyvalue storage.
    #status_type = models.CharField(max_length=10,
    #  verbose_name=_('current status'), blank=True)

    # last known vCard photo (hexdigest of SHA1 checksum, actually. should
    # always be of length 40 itself). It should be user-specific, not
    # contact-specific, but there's no more appropriate place for it (can
    # possibly store in the added avatar's filename/object, though).
    photosum = models.CharField(max_length=42, 
      verbose_name=_('photo checksum'), blank=True)
    # ? Need any other fields?

    def __unicode__(self):
        return '%s - %s' % (self.remote, self.local)

    class Meta:
        verbose_name = _('xmpp contact')
        verbose_name_plural = _('xmpp contacts')
        unique_together = ("remote", "local")


class UserJID(models.Model):
    """ User setting that allows used to define an XMPP JID which would be
    associated with the user (and will have full access to that user).  """

    user = models.OneToOneField(User, unique=True,
      verbose_name=_("User"), related_name='userjid')
    jid = models.EmailField(
      unique = True, blank = True, null = True,
      help_text = _('Jabber ID (that gets full access to the account)'),
      verbose_name=_('jid'))

