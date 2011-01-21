"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the face-part, which tries to return some response for entered command.
"""

import django
from django.utils.translation import ugettext as _

import logging
_log = logging.getLogger('xmppface')
# Debug...
import traceback

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
        _log.warn("\n --------------- Exception %r on "
          "GET_OR_CREATE." % e)
        _log.debug(traceback.format_exc())
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
    # Send XMPP iq request for vcard.
    iqreq = XmppIq(type='get', src=local, dst=remote, 
     content='<vCard xmlns="vcard-temp"/>')
    send_xmpp_message(iqreq)
     
def processcmd(**indata):
    """
    Gets a source jid and command text and returns XmppResponse.

    Should get no unkeyworded arguments.
    """
    src = indata.get('src')
    srcbarejid = src.split("/")[0]  # Strip the resource if any.
    dst = indata.get('dst')
    body = indata.get('body')
    _log.debug(" -+-+-+-+-+- indata: %r." % indata)
    if 'auth' in indata:  # Got subscribe/auth data. Save it.
        makecontact(dst, src)
        _log.debug(' ....... auth data. ')
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
            _log.warn(" --------------- Unexpected failure"
             " on updating auth data. Upd is %d." % upd)
        _log.debug(' ....... changed contact auth.')
        return  # Nothing else should be in there.
    if 'stat' in indata:  # Got contact status. Save it.
        _log.debug(' ....... status message.')
        # ! ^ Don't really care about status now. But save the last status
        # anyway.
        statustype = indata['stat']
        cache.set('st_%s'%src, statustype)  # bot's JID is ignored here.
        _log.debug(' ....... changed contact status.')
        if 'photo' in indata and indata['photo']:
            _log.debug(' ... + photo data.')
            check_photo_update(dst, src, indata['photo'])
        return
    # ... otherwise it's probably a user command.

    _log.debug("\n ------- src: %r; body: %r" % (src, body))
    request = XmppRequest(srcbarejid)
    
    # ! body should always be an unicode string here. If not - should change
    # ! processcmd's callers.
    #_log.debug("\n ------- bodystr: body: %r\n" % (body))
    try:
        # ! State-changing might be required, e.g. for multi-part commands.
        #_log.debug("\n ------- resolving...")
        callback, callback_args, callback_kwargs = cmdresolver.resolve(body)
        
        # Populate request.POST from body
        request, callback_kwargs = process_post_kwargs(request,
          callback_kwargs)

        _log.debug("\n ------- callback: %r (%r, %r); POST: %r" % (
          callback, callback_args, callback_kwargs, request.POST))

        # ...Also, middleware? it's not likely to support XmppResponse though.

        try:
            response = callback(request, *callback_args, **callback_kwargs)

            # ! We do expect an XmppResponse here. May construct one, but...
            if not isinstance(response, XmppResponse):
                _log.error("\n ------- callback (%r (%r, %r)) has "
                  "returned non-XmppResponse object %r." % (callback,
                  callback_args, callback_kwargs, response))
                raise TypeError("Response is not XmppResponse!")

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
            _log.error("\n --------------- Exception %r when calling "
                "callback: " % e)
            _log.debug(traceback.format_exc())
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
