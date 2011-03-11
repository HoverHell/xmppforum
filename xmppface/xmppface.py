""" This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the face-part, which tries to return some response for an entered
command.  """

import django
from django.utils.translation import ugettext as _

import logging
_log = logging.getLogger('xmppface')
import traceback  # Debug...


from .xmppbase import (XmppRequest, XmppIq, XmppResponse, 
  send_xmpp_message)
# Dumping of extra info into there:
from .models import XMPPContact
from .util import RegexCmdResolver, get_user_qs

from django.core.cache import cache


# ? XXX: Allow overriding ROOT_CMDCONF in settings?
cmdresolver = RegexCmdResolver("", "cmds")


def process_post_kwargs(request, kwargs):
    """ Retreives all 'POST_' (and 'GET_') keys from kwargs and adds them to
    the request's POST/GET data.  Returns tuple of (request, kwargs)
    modifying actual request.  """
    newkwargs = {}
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
    """ Bunch of race-condition-avoiding hacks to make sure specified unique
    XMPPContact object exists and can be update()'d.  """
    try:
        contact, created = XMPPContact.objects.get_or_create(
          local=local, remote=remote)
    except Exception, exc:
        _log.warn("\n --------------- Exception %r on "
          "GET_OR_CREATE." % exc)
        _log.debug(traceback.format_exc())
        ## ! XXX: Might be necessary:
        ## http://stackoverflow.com/questions/2235318/
        django.db.transaction.commit()
        contact = XMPPContact.objects.get(local=local, remote=remote)
    return contact


# ! FIXME: Move those two to some special view handlers.
def check_photo_update(local, remote_b, photo):
    """ See if we don't use the advertised contact's photo (avatar) and
    request it if necessary. """
    # Might want to optimize (cache) this.
    # ! XXX: for user with >1 bot contacts, vCard would be requested many
    #  times.
    contact = makecontact(local, remote_b)
    if contact.photosum == photo:
        return  # No need to update.
    # Could probably get that by moving it all into view. Although this is a
    # controversial architectural decision.
    if not get_user_qs(remote_b).exists():  # not registered.
        return
    # Send XMPP iq request for vcard.
    # XEP-0054, XEP-0153.
    # ? id=''.join(random.choice(string.ascii_lowercase + string.digits
    #     ) for x in range(4))
    # ? Appropriate to send it ti the base JID?
    iqreq = XmppIq(iqtype='get', src=local, dst=remote_b,
      content=u'<vCard xmlns="vcard-temp"/>')
    print "iqreq: %r" % iqreq
    send_xmpp_message(iqreq)
    # Save new photo checksum.
    # ! XXX: Might be problematic if user fails to answer this Iq request
    # Possible: conpute checksum of the received data (for saving it).
    # Also, check gajim source?
    upd = XMPPContact.objects.filter(local=local,
      remote=remote_b).update(photosum=photo)
    print "... done."


def update_vcard(local, remote_b, vcard):
    """ Process a received vCard data.  Saves vCard photo as user's avatar
    if possible. """
    """ example:
     {u'DESC': u'something',
      u'PHOTO': {
        u'BINVAL': u'\niVBORw0KGgoAAAANSUhE...\n...\nAAAAAElFTkSuQmC\nC',
        u'TYPE': u'image/png'}
     }
    """
    # same bit as in check_photo_update above
    _log.debug("update_vcard.")
    try:
        # ! XXX: avatar_file_path might be quite version-specific.
        from avatar.models import Avatar, avatar_file_path
    except ImportError:
        _log.debug("... could not import Avatar model!")
        return  # nothing to do then.
    user_qs = get_user_qs(remote_b)
    if not user_qs:
        _log.debug(" ... vCard for an unregistered JID!")
        return
    user = user_qs[0]
    photo = vcard.get('PHOTO')
    if not isinstance(photo, dict):
        _log.debug("... no usable PHOTO data!")
        return  # something's not here.
    import base64
    binval = photo.get('BINVAL')
    phtype = photo.get('TYPE')
    extension = phtype.split('/')[-1]  # file extension - simple way.
    try:
        pdata = base64.decodestring(binval)
    except Exception, exc:
        _log.warn("Exception %r on vCard BINVAL decoding." % exc)
        _log.debug(traceback.format_exc())
        return
    from django.core.files.base import ContentFile
    contentf = ContentFile(pdata)
    _log.debug("... creating avatar...")
    #contentf.name = 'xf-vcard-auto-avatar'
    autobasename = 'xf-vcard-auto-avatar.%s'
    contentf.name = autobasename % extension
    autoav = Avatar(user=user, avatar=contentf)
    # Check if auto-avatar is already presemt, replace if it is.
    # ! It's user's problem if user uploads an avatar with such a special
    #  name :)
    old_autoav_qs = Avatar.objects.filter(user=user,
      avatar__startswith=avatar_file_path(autoav, autobasename % ''))[:1]
    if old_autoav_qs:  # Already have some. Replace it.
        # ! XXX: non-parallel-safe here.
        old_autoav = old_autoav_qs[0]
        autoav.primary = old_autoav.primary  # XXX: Not very nice.
        old_autoav.delete()
    else:  # save the new one,
        autoav.save()
    _log.debug("... av done.")


def processcmd(indata):
    """ Processes XMPP-originating data such as statuses, text commands,
    etc.  """
    src = indata.get('src')
    srcbarejid = src.split("/")[0]  # Strip the resource if any.
    dst = indata.get('dst')
    body = indata.get('body')
    _log.debug(" -+-+-+-+-+- indata: %r." % indata)
    if 'auth' in indata:  # Got subscribe/auth data. Save it.
        makecontact(dst, src)  # ! XXX: dst/resource?
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
          remote=srcbarejid).update(**subsmapping[authtype])
        if upd != 1:  # ...something happened to be wrong anyway.
            _log.warn(" --------------- Unexpected failure"
              " on updating auth data. Upd is %d." % upd)
        return  # Nothing else should be in there.
    if 'stat' in indata:  # Got contact status. Save it.
        # ! ^ Don't really care about status now. But save the last status
        # anyway.
        statustype = indata['stat']
        cache.set(u'st_%s' % src, statustype)  # bot's JID is ignored here.
        if 'photo' in indata and indata['photo']:
            _log.debug(' ... + photo data.')
            check_photo_update(dst, srcbarejid, indata['photo'])
        return
    if 'vcard' in indata:
        _log.debug(' ....... vCard data.')
        update_vcard(dst, srcbarejid, indata['vcard'])
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
            
            _log.debug(" ... response: %r" % response)

            # ! We do expect an XmppResponse here. May construct one, but...
            if not isinstance(response, XmppResponse):
                _log.error("\n ------- callback (%r (%r, %r)) has "
                  "returned non-XmppResponse object %r." % (callback,
                  callback_args, callback_kwargs, response))
                raise TypeError("Response is not XmppResponse!")

            # May also add registration offer to anonymous users.
        except django.http.Http404, exc:
            # Using Http404 here is more simple.
            # ! TODO: Add support for handler404, etc?
            response = XmppResponse("404: %s" % exc)
        except django.core.exceptions.PermissionDenied, exc:
            response = XmppResponse(_("Access Denied.") + " %s" % exc)
        except Exception, exc:
            _log.error("\n --------------- Exception %r when calling "
                "callback: " % exc)
            _log.debug(traceback.format_exc())
            response = XmppResponse(_("Sorry, something went wrong!\n" \
              "Don't worry, admins weren't notified!"))
        # Not final. Also, toResponse(), part 1.
    except django.http.Http404, exc:  # Http404 from resolver.
        response = XmppResponse(_("No such command. Try 'HELP', maybe?"))
    # Return back with exactly the same full JIDs.
    response['src'] = dst
    response['dst'] = src
    #response['subject'] = "Jaboard: XMPP"
    # ? Populate other values from received data?
    send_xmpp_message(response)

