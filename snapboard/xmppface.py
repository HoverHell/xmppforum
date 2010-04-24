"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the face-part, which tries to return some response for entered command.
"""

import django
from django.utils.translation import ugettext as _

# cmdresolver / urlresolver. May be a hack..
from django.core.urlresolvers import RegexURLResolver
# Now that's surely a hack, eh?
from cmds import cmdpatterns

from xmppbase import *
from models import XMPPContact  # Dumping of meta into there.

# Couple of things here should probably be in a class.
# ? Place something instead of "", maybe?
cmdresolver = RegexURLResolver("", cmdpatterns)

# Debug...
import sys
import traceback

def process_post_kwargs(request, kwargs):
    """
    Retreives all 'POST_' (and 'GET_') keys from kwargs and adds them to the
    request's POST/GET data.  Returns tuple of (request, kwargs) modifying
    actual request.
    """
    newkwargs={}
    if not getattr(request, 'POST', None):
        request.POST = {}
    if not getattr(request, 'GET', None):
        request.GET = {}
    for key, value in kwargs.iteritems():
        if key.startswith('POST_'):
            request.POST[key[5:]] = value
        elif key.startswith('GET_'):
            request.GET[key[4:]] = value
        else:
            newkwargs[key] = value
    return (request, newkwargs)


def processcmd(**indata):
    """
    Gets a source jid and command text and returns XmppResponse.

    Should get no unkeyworded arguments.
    """
    src = indata.get('src')
    dst = indata.get('dst')
    body = indata.get('body')
    sys.stderr.write(" -+-+-+-+-+- D: indata: %r.\n" % indata)
    if 'auth' in indata:  # Got subsrtibe/auth data. Save it.
        sys.stderr.write(' ....... auth data. ')
        authtype = indata['auth']
        contact, created = XMPPContact.objects.get_or_create(
          local=dst, remote=src)
        if authtype == 'subscribed':
            contact.auth_to = True  # ! Hopefully not mistaken with auth_from
            sys.stderr.write(' ....... subscribed ')
        elif authtype == 'unsubscribed':
            contact.auth_to = False
            sys.stderr.write(' ....... unsubscribed ')
        elif authtype == 'subscribe':
            contact.auth_from = True
            sys.stderr.write(' ....... subscribe ')
        elif authtype == 'unsubscribe':
            contact.auth_from = False
            sys.stderr.write(' ....... unsubscribe ')
        sys.stderr.write(' ....... changed contact data. ')
        contact.save()  # Update the data
        sys.stderr.write(' ....... saved. ')
        return  # Nothing else should be in there.
    if 'stat' in indata:  # Got contact status. Save it.
        statustype = indata['stat']
        contact, created = XMPPContact.objects.get_or_create(
          local=dst, remote=src)
        contact.status_type = statustype
        sys.stderr.write(' ....... changed contact status. ')
        contact.save()
        sys.stderr.write(' ....... saved. ')
        return
    # ... otherwise it's a user command.

    sys.stderr.write("\n ------- D: src: %r; body: %r\n" % (src, body))
    srcbarejid = src.split("/")[0]  # Strip the resource if any.
    request = XmppRequest(srcbarejid)
    
    # ! body should always be an unicode string here. If not - should change
    # ! processcmd's callers.
    #sys.stderr.write("\n ------- D: bodystr: body: %r\n" % (body))
    try:
        # ! State-changing might be required, e.g. for multi-part commands.
        #sys.stderr.write("\n ------- D: resolving...")
        callback, callback_args, callback_kwargs = cmdresolver.resolve(body)
        
        # Populate request.POST from body
        request, callback_kwargs = process_post_kwargs(request,
          callback_kwargs)

        sys.stderr.write(("\n ------- D: callback: %r; args: %r; kwargs: %r; "+\
          " post: %r\n") % \
          (callback, callback_args, callback_kwargs, request.POST))

        # ...Also, middleware? it's not likely to support XmppResponse though.

        try:
            response = callback(request, *callback_args, **callback_kwargs)

            # ! We do expect an XmppResponse here. May construct one, but...
            if not isinstance(response, XmppResponse):
                sys.stderr.write("\n ------- E: callback (%r (%r, %r))" % \
                  (callback, callback_args, callback_kwargs) + \
                  " returned non-XmppResponse object %r.\n" % response)
                raise TypeError("Response is not response!")

            # May also add registration offer to anonymous users.
        except django.http.Http404, e:
            # Using Http404 here not very right, eh?
            # But is certainly more simple.
            response = XmppResponse("404: %s" % e)
        except django.core.exceptions.PermissionDenied, e:
            response = XmppResponse(_("Access Denied.") + " %s"%e)
        except Exception, e:
            response = XmppResponse(_("Sorry, something went wrong!\n" \
              "Don't worry, admins weren't notified!"))
            sys.stderr.write("\n --------------- E: Exception when calling callback:")
            sys.stderr.write(traceback.format_exc())
        # Not final. Also, toResponse(), part 1.
    except django.http.Http404, e:  # Http404 from resolver.
        response = XmppResponse(_("No such command. Try 'HELP', maybe?"))
    # Return back with exactly the same full JIDs.
    response['src'] = dst
    response['dst'] = src
    #response['subject'] = "Jaboard: XMPP"
    # ? Populate other values from received data?
    return response

# Testing:
#processcmd("hell@hell.orts.ru", "bot@bot.hell.orts.ru", "#")
