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
# Dumping of extra info into there:
import models
from models import XMPPContact, cachefetch
from django.core.cache import cache

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
    # Those two checks shouldn't actually be necessary.
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

def makecontact(local, remote):
    '''
    Bunch of race-condition-avoiding hacks to make sure specified unique
    XMPPContact object exists and can be update()'d.
    '''
    try:
        contact, created = XMPPContact.objects.get_or_create(
          local=local, remote=remote)
    except Exceltion, e:
        sys.stderr.write("\n --------------- E: Exception %r on "\
         " GET_OR_CREATE: \n"%(e,))
        sys.stderr.write(traceback.format_exc())
        ## Might be necessary:
        ## ref. http://stackoverflow.com/questions/2235318/how-do-i-deal-with-this-race-condition-in-django
        django.db.transaction.commit()
        contact = XMPPContact.objects.get(local=local, remote=remote)
    return contact

def check_photo_update(local, remote, photo):
    # Might want to optimize (cache) this.
    contact = makecontact(local, remote)
    if contact.photo == photo:
        return  # No need to update.
    barejid = remote.split('/')[0]  # ! status gets a full JID... usually.
    # Could probably get that by moving it all into view. Although this is a
    # controversial architectural decision.
    if not models.User.objects.filter(sb_usersettings__jid__exact=barejid).exists():
        # not registered.
        return
    # Send XMPP request for vcard.
    # !!...

def processcmd(**indata):
    """
    Gets a source jid and command text and returns XmppResponse.

    Should get no unkeyworded arguments.
    """
    src = indata.get('src')
    srcbarejid = src.split("/")[0]  # Strip the resource if any.
    dst = indata.get('dst')
    body = indata.get('body')
    sys.stderr.write(" -+-+-+-+-+- D: indata: %r.\n" % indata)
    if 'auth' in indata:  # Got subscribe/auth data. Save it.
        makecontact(dst, src)
        sys.stderr.write(' ....... auth data. ')
        authtype = indata['auth']
        subsmapping = {
         'subscribed': {'auth_to': True},
         'unsubscribed': {'auth_to': False},
         'subscribe': {'auth_from': True},
         'unsubscribe': {'auth_from': False}
        }
        # That one should be minimalistic & atomic.
        upd = XMPPContact.objects.filter(local=dst,
         remote=src).update(**subsmapping[authtype])
        if upd != 1:  # ...something happened to be wrong anyway.
            sys.stderr.write("\n --------------- E: Unexpected failure"\
             " on updating auth data. Upd is %d.\n"%upd)
        sys.stderr.write(' ....... changed contact auth.\n')
        return  # Nothing else should be in there.
    if 'stat' in indata:  # Got contact status. Save it.
        sys.stderr.write(' ....... status message. ')
        # ! ^ Don't really care about status now. But save the last status
        # anyway.
        statustype = indata['stat']
        cache.set('st_%s'%src, statustype)  # bot's JID is ignored here.
        sys.stderr.write(' ....... changed contact status. \n')
        if 'photo' in indata and indata['photo']:
            sys.stderr.write(' ... + photo data. ')
            check_photo_update(dst, src, indata['photo'])
        return
    # ... otherwise it's probably a user command.

    sys.stderr.write("\n ------- D: src: %r; body: %r\n" % (src, body))
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
            sys.stderr.write("\n --------------- E: Exception %r when calling callback: \n"%(e,))
            sys.stderr.write(traceback.format_exc())
        # Not final. Also, toResponse(), part 1.
    except django.http.Http404, e:  # Http404 from resolver.
        response = XmppResponse(_("No such command. Try 'HELP', maybe?"))
    # Return back with exactly the same full JIDs.
    response['src'] = dst
    response['dst'] = src
    #response['subject'] = "Jaboard: XMPP"
    # ? Populate other values from received data?
    send_xmpp_message(response)

# Testing:
#processcmd("hell@hell.orts.ru", "bot@bot.hell.orts.ru", "#")
