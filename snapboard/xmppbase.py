"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the base-part, that provides some classes and wrappers necessary for
that.
"""

import django
from django.shortcuts import render_to_response as render_to_response_orig
# User class is customized, so not importing it from django itself.
from models import User

import simplejson  # For serialization of XmppResponse


class XmppRequest(object):
    """
     XmppRequest is a class partially compatible with HttpRequest, so it can
     be used as a request variable in the views.

     It doesn't provide most of the data now, though, so using it now with
     html templates is not only wrong but also impossible.
    """

    def __init__(self, srcjid):
        # This isn't really meant for anything yet.
        self.srcjid = srcjid
        # "Authentication":
        try:
            self.user = User.objects.get(sb_usersettings__jid__exact=srcjid)
        except User.DoesNotExist:
            self.user = django.contrib.auth.models.AnonymousUser()
            # ? Just create one? Or he should be offered to register?
        # Populating extra fields:
        self.META = {'REMOTE_ADDR': srcjid}
        self.POST = None
        # Stuff ftom HttpRequest:
        #self.GET, self.POST, self.COOKIES, self.META, self.FILES = None, \
        #  None, None, {}, {}, {}, {}, {}


class XmppResponse(dict):
    """
    Possibly unnecessary object, analogous to HttpResponse.

    Can be used for any XMPP message.

    Currently it is a subclass of dict with few extras.
    """
    def __init__(self, html=None, body=None, src=None, dst=None, id=None):
        # Current default is to create XHTML-message and construct plaintext
        # message from it.
        self['html'] = html
        if body == None:
            # ?? Have to do something else?
            self['body'] = django.utils.encoding.force_unicode(
              django.utils.html.strip_tags(html)).replace(
                '&amp;', '&').replace('&lt;', '<').replace(
                  '&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
        else:
            self['body'] = body
        # ! Source address to use has to be in XMPP server's domain, at
        # least.  Should usually be created from request message's
        # destination or some default value.
        self['src'] = src
        # ? May contain a resource?
        # ! Destination address should be ckecked somewhere for having
        # XMPP-authenticated any jid on this server, probably.
        self['dst'] = dst
        # ! Id doesn't seem to change much, but might happen to be
        # necessary.
        self['id'] = id

    def __str__(self):
        """
        Serializes itself into simplejson string.
        """
        return simplejson.dumps(self)  # Should be string.


def render_to_response(*args, **kwargs):
    """
    A render_to_response wrapper that allows using it for both HttpRequest
    and XmppRequest.
    """

    # There should be other ways to determine an Xmpp request, no?
    # Or it would be 'other function'.
    # Also, may args[0] not possibly contain template name?
    try:
        IsXmpp = isinstance(kwargs['context_instance']['request'], XmppRequest)
    except:
        IsXmpp = False
    if IsXmpp:
        args = (args[0] + '.xmpp',) + args[1:]  # Fix template name.
        # Return some XmppResponse with rendered template.
        return XmppResponse(django.template.loader.render_to_string(*args, **kwargs))
    else:
        # Not Xmpp. Not our business.
        args = (args[0] + '.html',) + args[1:]  # ...
        return render_to_response_orig(*args, **kwargs)
