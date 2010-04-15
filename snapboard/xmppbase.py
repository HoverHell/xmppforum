"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the base-part, that provides some classes and wrappers necessary for
that.
"""

import django

import sys

# For send_xmpp_message
from django.conf import settings
# ! AF_UNIX socket is currently used.
XMPPOUTQUEUEADDR = getattr(settings, 'SOCKET_ADDRESS', 'xmppoutqueue')
import socket
xmppoutqueue = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
# Also, only one connection call. Might be insufficiently reliable.
try:
    xmppoutqueue.connect(XMPPOUTQUEUEADDR)
except:
    sys.stderr.write(" ERROR: could not connect to xmppoutqueue!\n")

# For render_to_response wrapper
from django.shortcuts import render_to_response as render_to_response_orig

# for login_required wrapper
from django.contrib.auth.decorators import login_required as login_required_orig

# For success_or_reverse_redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

# For notification sending wrapper
try:
    from notification.models import send as notification_send_orig
    from notification import models as notification
except ImportError:
    notification = None

import re  # Stripping XHTML images.

#lastnewlinere = re.compile("\n+$")  # Stripping extraneous newlines.


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
        # User class is customized, so not importing it from django itself.
        from models import User  # Also, avoiding circular imports.
        # ! Maybe it should be done in xmppface?
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
    def __init__(self, html=None, body=None, src=None, dst=None, id=None,
      user=None):
        # Current default is to create XHTML-message and construct plaintext
        # message from it.
        self.setuser(user)  # For minding the usersettings.
        if html is not None:
            self.setxhtml(html)
            # ! Don't usually allow to set both body and html.
        elif body is not None:
            self['body'] = body.rstrip()  # ! Is rstrip certainly not problematic?
        else:
            self['body'] = '(something went wrong?)'
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

    def setuser(self, user):
        from views import get_user_settings  # beware of cyclic imports
        self.user = user or django.contrib.auth.models.AnonymousUser()
        self.usersettings = get_user_settings(self.user)
        
    def setxhtml(self, html):
        # Usersettings are considered here
        # ! Note that changing user afterwards wouldn't change this.
        if not(self.usersettings.disable_xmpp_xhtml):
            if (self.usersettings.disable_xmpp_images):
                self['html'] = self.imgfix(html)
            else:
                self['html'] = html
        # Body is set forcibly for less possible confusion. Although, some
        # alteration (warning, for example) is possible here.
        # Note: in Psi, non-XHTML body is used in displayed notifications.
        # ? Add warning message to the end?
        # Remove formatting. Also, it should be XML-compatible.
        # ! Probably should replace <a> tags with some link representation.
        # ! Or even always add actual link to the tag.
        self['body'] = django.utils.encoding.force_unicode(
          django.utils.html.strip_tags(self.imgfix(html))).rstrip()  # ! See above on rstrip.
          
    def imgfix(self, htmlsource):
        """
        Replaces all <img> tags in htmlsource with some more
        plaintext-representative form.
        """
        img_tag_re=re.compile(r"</?img((\s+(\w|\w[\w-]*\w)(\s*=\s*" \
          "(?:\".*?\"|'.*?'|[^'\">\s]+))?)+\s*|\s*)/?>")  # Horrible but proper.
        # ? Where should be all those compiled regexes stored?
        def img_repr(imgstr):
            """
            Converts an HTML img tag string into informative plaintext:
            [image: http://some/img.png alt:"..." title:"..."]
            """
            img_param_re=r"(%s)\s*=\s*(\".*?\"|'.*?'|[^'\">\s]+)"
            img_src_re = re.compile(img_param_re%"src")  # More special for us.
            repr_params = ["alt", "title"] # Generic interesting params.
            srcmatch = img_src_re.search(imgstr)
            if srcmatch:
                result='[image: '+srcmatch.groups()[1]
                for param in repr_params:
                    parammatch = re.search(img_param_re%param, imgstr)
                    if parammatch:
                        result += ' %s: %s' % (param,
                          parammatch.groups()[1])
                result += '] '
                return result
            else:  # No src? Not a proper image (or a closing tag)
                return ''
        #return img_tag_re.sub(lambda x: img_repr(x.groups()[0]), htmlsource);
        # !! More simple version - for now.
        return img_tag_re.sub(u"[img]", htmlsource);
        #  Yeah, couldn't figure out how to do all that with one regexp.

    def __str__(self):
        """
        Serializes itself into string.
        """
        # For optimization, some XML serialization happens here.
        # Parse self, hah.
        selfrepr = {}
        content = ''
        for key, value in self.iteritems():
            if key == 'html':
                content = content + "<html xmlns='"\
                  "http://jabber.org/protocol/xhtml-im'><body "\
                  "xmlns='http://www.w3.org/1999/xhtml'>" + value + \
                  "</body></html>"
            elif key == "body":
                content = "<body>" + value + "</body>" + content
            elif key == "subject":
                content = "<subject>" + value + "</subject>" + content
            else:
                selfrepr[key] = value  # Handle everything else over there.
        selfrepr['content'] = content
        return simplejson.dumps(selfrepr)  # Should be string.

def send_xmpp_message(msg):
    """
    Common function to send a XMPP message through running XMPP connection
    provider. Should generally be called with XmppResponse argument with all
    necessary fields set.
    """
    # It uses global pre-initialized xmppoutqueue connection.
    try:
        # msg decides itself on how to be dumped.
        xmppoutqueue.send(str(msg))  
    except:  # ! Should do more reliability increasing here.
        sys.stderr.write(" ERROR: Could not write to xmppoutqueue!\n")
        sys.stderr.write("    Message was: %s.\n" % str(msg))

def render_to_response(*args, **kwargs):
    """
    A render_to_response wrapper that allows using it for both HttpRequest
    and XmppRequest.
    """

    # There should be other ways to determine an Xmpp request, no?
    # Or it would be 'other function'.
    # Also, may args[0] not possibly contain template name?
    try:
        request = kwargs['context_instance']['request']
        IsXmpp = isinstance(request, XmppRequest)
    except:  # Something is not right, but it's probably not XMPP anyway.
        request = None
        IsXmpp = False
    if IsXmpp:  # Return some XmppResponse with rendered template.
        args = (args[0] + '.xmpp',) + args[1:]  # Fix template name.
        return XmppResponse(
          django.template.loader.render_to_string(*args, **kwargs), 
          user=request.user)
    else:  # Not Xmpp. Not our business.
        args = (args[0] + '.html',) + args[1:]  # ...
        return render_to_response_orig(*args, **kwargs)

def login_required(function=None):
    http_login_required = login_required_orig(function)
    def decorate(request, *args, **kwargs):  # request is explicit.
        if isinstance(request, XmppRequest):
            if request.user.is_authenticated:
                function(request, *args, **kwargs)
            else:
                pass  # ! Access denied and offer registration here.
        else:  # Not XMPP. use original decorated.
            http_login_required(request, *args, **kwargs)
    return decorate

def anonymous_login_required(function=None):
    def decorate(request, *args, **kwargs):
        if request.user.is_authenticated:
            function(request, *args, **kwargs)
        else:  # Use Anonymous!
            # Just for this request, of course.
            request.user = User.objects.get(username=settings.ANONYMOUS_NAME)
            function(request, *args, **kwargs)
    return decorate

def direct_to_template(request, template):
    if isinstance(request, XmppRequest):  # At least it's XMPP.
        # Not adding '.xmpp' here.
        return XmppResponse(
          django.template.loader.render_to_string(template,
          context_instance=django.template.RequestContext(request)))
    # ! May need direct_to_template_orig?

def success_or_reverse_redirect(*args, **kwargs):
    # Remove reverse()-irrelevant parts of kwargs:
    req = kwargs.pop("req")  # Should always be present, actually.
    msg = kwargs.pop("msg", "Success.")
    if isinstance(req, XmppRequest):
        return XmppResponse(msg)
    else:  # HTTP / redirect to reverse of view.
        return HttpResponseRedirect(reverse(*args, **kwargs))

def send_notifications(users, label, extra_context=None, on_site=True,
  **etckwargs):
    if not notification:
        return
    from notification.models import Notice, NoticeType, Site, get_language,\
      get_notification_language, activate, get_formatted_messages, \
      should_send, send_mail, LanguageStoreNotAvailable, Context, ugettext
    
    remaining_users = []
    print(" D: Notifier: users: %r" % users)
    # ! Note: queueing is disregarded for XMPP notifications.
    # !!! Most of this is copied from send_now
    if extra_context is None:
        extra_context = {}

    notice_type = NoticeType.objects.get(label=label)

    current_site = Site.objects.get_current()
    notices_url = u"http://%s%s" % (
        unicode(current_site),
        reverse("notification_notices"),
    )

    current_language = get_language()

    for user in users:
        
        jid = None
        try:
            jid = user.sb_usersettings.jid
        except:
            pass
        if not jid: # Not jid available. Leave him to usual notification.
            remaining_users.append(user)
            continue  # ! What if it's not XMPP-related notification at all?
        # !!! Also, should check if user is authorized in XMPP and (maybe)
        # !!! is online (which may better be configurable).
        
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

        # Strip newlines from subject
        #subject = ''.join(render_to_string('notification/email_subject.txt', {
        #    'message': messages['short.txt'],
        #}, context).splitlines())
        body = django.template.loader.render_to_string(
          'notification/%s/xmpp.html'%label,
          context_instance=context)

        #notice = Notice.objects.create(user=user, message=messages['notice.html'],
        #    notice_type=notice_type, on_site=on_site)
        #if should_send(user, notice_type, "1") and user.email: # Email
        #    recipients.append(user.email)
        # !!!
        noticemsg = XmppResponse(body, src="bot@bot.hell.orts.ru", dst=jid,
          user=user)
        send_xmpp_message(noticemsg)

    # reset environment to original language
    activate(current_language)

    print(" D: Notifier: remaining users: %r" % remaining_users)
    
    # Send remaining (non-XMPP) notifications.
    notification_send_orig(remaining_users, label, extra_context, on_site,
      **etckwargs)
if notification:  # ! Deeping the hax in.
    notification.send = send_notifications
