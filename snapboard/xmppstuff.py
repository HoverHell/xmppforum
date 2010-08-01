"""
Additional wrappers for XMPP-enabled django app, importable from models.

Currently contains only notification wrapper, that probably shouldn't be
implemented this way in the first place.
"""

try:
    from notification.models import send as notification_send_orig
    from notification import models as notification
except ImportError:
    notification = None

from notification.models import Notice, NoticeType, Site, get_language,\
  get_notification_language, activate, get_formatted_messages, \
  should_send, send_mail, LanguageStoreNotAvailable, Context, ugettext

import django  
from django.core.urlresolvers import reverse
from xmppbase import XmppResponse, XmppPresence, send_xmpp_message

#from models import XMPPContact

def send_notifications(users, label, extra_context=None, on_site=True,
  xmppresources=None, **etckwargs):
    '''
    ...
    '''
    if not notification:
        return

    import models
    
    remaining_users = []
    print(" D: Notifier: users: %r" % users)
    # ! Note: queueing is disregarded for XMPP notifications.
    # !!! Most of this is copied from send_now
    if extra_context is None:
        extra_context = {}
    if xmppresources is None:
        xmppresources = {}

    notice_type = NoticeType.objects.get(label=label)

    current_site = Site.objects.get_current()
    notices_url = u"http://%s%s" % (
        unicode(current_site),
        reverse("notification_notices"),
    )

    current_language = get_language()

    # Probably can do ucontacts = ... filter(remote__in=userjids)

    for user in users:
        
        jid = None
        try:  # If user has got jid at all.
            jid = user.sb_usersettings.jid
        except:
            pass

        # If user has authenticated some bot.
        ucontacts = models.XMPPContact.objects.filter(remote=jid, auth_to=True)
        # Also, we don't care about user's status now.
        
        if not (jid and ucontacts):
            # Not jid/contact available. Leave him to e-mail notification.
            if user.email:
                print(" D: Notifier: using e-mail for %r." % user)
                remaining_users.append(user)
            else:
                print(" D: Notifier: cannot contact %r." % user)
            # Or to none/on-site.
            # ! Will on-site notifications work with that?
            continue  # ! What if it's not XMPP-related notification at all?
        
        # srcjid = "bot@bot.hell.orts.ru"
        srcjid = ucontacts[0].local  # Choose first available authenticated bot JID.
        if user in xmppresources:
            srcjid += "/%s"%xmppresources[user]
            # ! Could be better to send status not every time. But not sure
            #  how to find out if have to re-send it.
            send_xmpp_message(XmppPresence(src=srcjid, dst=jid,
             show='chat', status='Here here!', priority="0"))

        # get user language for user from language store defined in
        # NOTIFICATION_LANGUAGE_MODULE setting
        try:
            language = get_notification_language(user)
        except LanguageStoreNotAvailable:
            language = None
        if language is not None:
            # activate the user's language
            activate(language)

        # update context with user specific translations
        context = Context({
            "user": user,
            "notice": ugettext(notice_type.display),
            "notices_url": notices_url,
            "current_site": current_site,
        })
        context.update(extra_context)

        body = django.template.loader.render_to_string(
          'notification/%s/xmpp.html'%label, context_instance=context)

        # ?..
        #message = django.template.loader.render_to_string(
        #  'notification/%s/notice.html'%label, context_instance=context)
        #notice = Notice.objects.create(user=user, message=message,
        #    notice_type=notice_type, on_site=on_site)
        noticemsg = XmppResponse(body, src=srcjid, dst=jid, user=user)
        send_xmpp_message(noticemsg)

    # reset environment to original language
    activate(current_language)

    print(" D: Notifier: remaining users: %r" % remaining_users)
    
    # Send remaining (non-XMPP) notifications.
    notification_send_orig(remaining_users, label, extra_context, on_site,
      **etckwargs)

if notification:  # ! Deeping the hax in.
    notification.send = send_notifications

