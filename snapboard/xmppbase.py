"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the base-part, that provides some classes and wrappers necessary for that.
"""

import django
from django.shortcuts import render_to_response as render_to_response_orig
from django.template import loader
#from django.contrib.auth.models import User
# User class is customized, so...
from models import User 

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
            # Just create one? Or it should be 
        # Populating extra fields:
        self.META = {'REMOTE_ADDR': srcjid}
        # Stuff ftom HttpRequest:
        #self.GET, self.POST, self.COOKIES, self.META, self.FILES = None, None, None, {}, {}, \
        #  {}, {}, {}

class XmppResponse(object):
    """
    Possibly unnecessary object, analogous to HttpResponse.
    
    But may be used for rendering the response (XML?) with consideration of
    in-message formatting.
    
    May add a subject, too.
    """
    def __init__(self, body=None):
        self.body = body
        # Source address to use. Have to be in XMPP server's domain, at
        # least.  Should usually be created from request message's
        # destination or some default value
        # ? May contain a resource?
        self.src = None
        # Destination address.
        # ! Somewhere it should be checked for having XMPP-authenticated the
        # server's contact, probably.
        self.dst = None
        # ? thread id?
        self.id = None
        
    def __str__(self):
        """
        Just returns the content for now.
        """
        return str(self.body) # String for sure.

def render_to_response(*args, **kwargs):
    """
    A render_to_response wrapper that allows using it for both HttpRequest
    and XmppRequest.
    """
    
    """
    is_xmpp = False
    if 'context_instance' in kwargs:
        # We have something, yes.
        context_instance = kwargs['context_instance']
        if 'request' in context_instance:
            # 'They' even provided a request to 'us'.
            request = context_instance['request']
            if isinstance(request, XmppRequest):
                is_xmpp = True
    # There should be other ways to determine an Xmpp request, no?
    # Or it would be 'other function'.
    # May args[0] not possibly contain template name?
    if is_xmpp:
    """
    if isinstance(kwargs['context_instance']['request'], XmppRequest):
        args = (args[0] + '.xmpp',) + args[1:] # ! Fix template name. 
        # Return some XmppResponse.
        return XmppResponse(loader.render_to_string(*args, **kwargs))
    else:
        # Not Xmpp. Not our business.
        args = (args[0] + '.html',) + args[1:] # ... 
        return render_to_response_orig(*args, **kwargs)
