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
import socket
import time  # periodic reconnect attempts
import copy
from thread import start_new_thread  # for reconnector thread

import logging
_log = logging.getLogger('xmppbase')

# for XmppReq/Resp...
from django.contrib.auth.models import AnonymousUser
# for login_required wrapper
from django.contrib.auth.decorators import login_required as \
  login_required_orig
# For success_or_reverse_redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
# For stripping XHTML images.
import re
# For serialization of XmppResponse.  Django uses best json available.
from django.utils import simplejson

from .util import get_user_or_anon, get_user_xfsettings

# Monkey-patch HttpRequest so it gets is_xmpp() as well.
import django.http
django.http.HttpRequest.is_xmpp = lambda self: False


# Can pretty much derive it from django.http.HttpRequest
class XmppRequest(object):
    """ XmppRequest is a class partially compatible with HttpRequest, so it
    can be used as a request variable in the views.

    It doesn't provide most of the data now, though, so using it now with
    html templates is not only wrong but is also usually impossible.  """

    def __init__(self, srcjid):
        self.srcjid = srcjid
        self.user = get_user_or_anon(srcjid)
        # Populating extra fields:
        self.META = {'REMOTE_ADDR': srcjid}
        self.POST, self.GET = {}, {}
        # Compatibility-convenuence stuff:
        self.path = None
        #self.COOKIES, self.FILES = None, {}

    def is_ajax(self):
        """ HttpRequest-compatible function. Returns False. """
        return False

    def is_xmpp(self):
        """ Request is XmppRequest and suggests that XmppResponse is
        expected.  """
        return True

    def __repr__(self):
        # ! TODO.
        return "<XmppRequest ...>"


class XmppResponse(dict):
    """ Possibly unnecessary object, analogous to HttpResponse.

    Can be used for any XMPP message.

    Currently it is a subclass of dict with few extras.  """
    def __init__(self, html=None, body=None, src=None, dst=None, id=None,
      user=None):
        self['class'] = 'message'
        # Current default is to create XHTML-message and construct plaintext
        # message from it.
        self.setuser(user)
        if html is not None:
            self.setxhtml(html)
            # ! Don't usually allow to set both body and html.
        elif body is not None:
            # ! Is rstrip certainly not problematic?
            self['body'] = body.rstrip()
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

    def setuser(self, user=None):
        self.user = user or AnonymousUser()
        # ! XXX: inappropriate dependency?
        # ! TODO: make a whole xmppface.UserSettings model then?
        self.usersettings = get_user_xfsettings(user)

    def setxhtml(self, html):
        # Usersettings are considered here
        # ! Note that changing user afterwards wouldn't change this.
        if not(self.usersettings.disable_xmpp_xhtml):
            if (self.usersettings.disable_xmpp_images):
                self['html'] = self.imgfix(html)
            else:
                self['html'] = html
        else:
            logging.debug("skipping HTML part on user's preferences.")
        # Body is set forcibly for less possible confusion. Although, some
        # alteration is possible here.
        # Note: in Psi, non-XHTML body is used in displayed notifications.
        # Remove formatting. Also, it should be XML-compatible.
        # ! Probably should replace <a> tags with some link representation.
        # ! Or even always add actual link to the tag.
        # ! See above on rstrip.
        #self['body'] = django.utils.encoding.force_unicode(
        #  django.utils.html.strip_tags(self.imgfix(html))).rstrip()
        import html2text
        self['body'] = django.utils.encoding.force_unicode(
          html2text.html2text(html)).rstrip()
    
    def imgfix(self, htmlsource):
        """
        Replaces all <img> tags in htmlsource with some more
        plaintext-representative form.
        """
        img_tag_re = re.compile(r"</?img((\s+(\w|\w[\w-]*\w)(\s*=\s*" \
          "(?:\".*?\"|'.*?'|[^'\">\s]+))?)+\s*|\s*)/?>")  # Horrible but proper.
        # ? Where should be all those compiled regexes stored?
        def img_repr(imgstr):
            """
            Converts an HTML img tag string into informative plaintext:
            [image: http://some/img.png alt:"..." title:"..."]
            """
            img_param_re = r"(%s)\s*=\s*(\".*?\"|'.*?'|[^'\">\s]+)"
            img_src_re = re.compile(img_param_re%"src")  # More special for us.
            repr_params = ["alt", "title"] # Generic interesting params.
            srcmatch = img_src_re.search(imgstr)
            if srcmatch:
                result = '[img: ' + srcmatch.groups()[1]
                for param in repr_params:
                    parammatch = re.search(img_param_re%param, imgstr)
                    if parammatch:
                        result += ' %s: %s' % (param,
                          parammatch.groups()[1])
                result += '] '
                return result
            else:  # No src? Not a proper image (or a closing tag)
                return ''
        #return img_tag_re.sub(lambda x: img_repr(x.groups()[0]), htmlsource)
        # !! More simple version - for now.
        return img_tag_re.sub(u"[img]", htmlsource)
        #  Yeah, couldn't figure out how to do all that with one regexp.

    def __str__(self):
        """ Serializes itself into string.  """
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
            elif key in ('body', 'subject'):
                content = "<%s>%s</%s>" % (key, value, key) + content
            else:
                selfrepr[key] = value  # Handle everything else over there.
        selfrepr['content'] = content
        return simplejson.dumps(selfrepr)  # Should be string.


class XmppIq(dict):
    """
    XmppResponse-like object for XMPP iq messages.
    """
    """
    Example:
    <iq type="get" to="hell@hell.orts.ru">
    <vCard xmlns="vcard-temp" version="2.0" 
     prodid="-//HandGen//NONSGML vGen v1.0//EN"/></iq>
    """
    def __init__(self, iqtype='get', **kwargs):
        """ Should (usually) get 'src', 'dst', 'content', possibly 'id' in
        kwargs.  """
        self['class'] = 'iq'
        self['type'] = iqtype
        self.update(kwargs)  # src, dst, id, content, ...

    def __str__(self):
        """ Serializes itself into string.  """
        return simplejson.dumps(self)


class XmppPresence(dict):
    """
    XmppResponse-like object for XMPP presence messages.
    """
    """
    Example:
<presence from="hoverhell1@jabber.ru/hheee" xml:lang="en"
 to="hell@hell.orts.ru/hheee">
<show>chat</show><status>FFC? FFS!</status><priority>0</priority></presence>
    """
    def __init__(self, **kwargs):
        """ Should (usually) get 'src', 'dst',
         and 'status', 'priority', 'show' (or 'content') in kwargs.  """
        self['class'] = 'presence'
        self.update(kwargs)

    def __str__(self):
        """ Serializes itself into string.  """
        selfrepr = {}
        content = ''
        for key, value in self.iteritems():
            if key in ('show', 'status', 'priority'):
                content = "<%s>%s</%s>" % (key, value, key) + content
            else:
                selfrepr[key] = value
        selfrepr['content'] = content
        return simplejson.dumps(selfrepr)


# XXX: Not very good to do that, but it works.
xmppoutqueue = None
connecting = True
unsent = []
def connkeeper():
    """
    A function that periodically tries to connect to the specifiet socket
    untill successful (or killed).
    """
    global xmppoutqueue
    global connecting
    global unsent
    XMPPOUTQUEUEADDR = getattr(settings, 'SOCKET_ADDRESS', 'var/xmppoutqueue')
    connecting = True
    # ! AF_UNIX socket is currently used.
    #xmppoutqueue = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    _log.debug("connecting to the xmppoutqueue...")
    xmppoutqueue = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # ? Move this stuff to settings: ?
    pause = 0.5  # current time to wait until retry
    pause_max = 4.0  # somewhat-around-maximum waiting time.
    while True:
        try:
            xmppoutqueue.connect(XMPPOUTQUEUEADDR)
        except Exception, whatever:
            if pause < pause_max:
                _log.warn("could not connect to the xmppoutqueue! Waiting "
                 "for %s seconds." % pause)
            elif abs(pause_max - pause) < 0.5:  # got to max.
                _log.error("could not connect to the xmppoutqueue!  Will "
                 "keep trying.")
                pause += 1
            time.sleep(pause)
            if pause < pause_max:
                pause *= 2  # wait 8 seconds at most, doubling on attempt.
            continue  # try again
        _log.debug("connected to the xmppoutqueue.\n")
        connecting = False
        processing = copy.copy(unsent)
        unsent = []
        for msg in processing:
            send_xmpp_message(msg)
        break  # success.
## Development: don't bother until there is something to be sent.
#start_new_thread(connkeeper, ())
connecting = False

def send_xmpp_message(msg):
    """
    Common function to send a XMPP message through running XMPP connection
    provider. Should generally be called with XmppResponse argument with all
    necessary fields set.
    
    Starts a connkeeper thread if necessary.
    """
    global xmppoutqueue
    global unsent
    # It uses global pre-initialized xmppoutqueue connection.
    try:
        # msg decides itself on how to be dumped.
        # And newline is used to split socket datastream into separate
        # messages.
        xmppoutqueue.send(str(msg)+"\n")
    except Exception:  # ! Should do more reliability increasing here.
        _log.warn("Could not write to xmppoutqueue! (reconnecting...)")
        _log.debug("    Message was: %s.\n" % str(msg))
        unsent.append(msg)
        _log.debug("x1")
        if not connecting:
            try:
                xmppoutqueue.close()
            except Exception:
                pass  # (probably it was None)
            _log.debug("    Starting the reconnector... ")
            start_new_thread(connkeeper, ())
        

def render_to_response(template_name, *args, **kwargs):
    """ A render_to_response wrapper that allows using it for both
    HttpRequest and XmppRequest.  `template_name` is explicit since it is
    modified to end with '.xmpp' or '.html' depending on the request.
    XMPP response rendering can only be used with RequestContext. """
    from django.shortcuts import render_to_response as render_to_response_orig
    # There should be other ways to determine an Xmpp request, no?
    # Or it would be 'other function'.
    # Also, may args[0] not possibly contain template name?
    try:
        request = kwargs['context_instance']['request']
        isxmpp = request.is_xmpp()
    except Exception:
        # Something is not right, but it's probably not XMPP anyway.
        request = None
        isxmpp = False
    if isxmpp:  # Return some XmppResponse with rendered template.
        # ! Wouldn't it be better to 's/(\.html)?$/.xmpp/' here?
        return XmppResponse(
          django.template.loader.render_to_string(
            re.sub(r'(\.html|\.xmpp)?$', '.xmpp', template_name),
            *args, **kwargs), 
          user=request.user)
    else:  # Not Xmpp. Not our business.
        ## Can even require using '.html' in calls, but likely should not.
        return render_to_response_orig(
            re.sub(r'(\.html)?$', '.html', template_name),
          *args, **kwargs)


def xmpp_loginreq_handler(request, function, *args, **kwargs):
    """ Default action (view) for an unregistered JID who tries to do
    something which is login_required. """
    return XmppResponse("Please register to do this.")


def get_login_required_wrapper(xmpp_unreg_view=xmpp_loginreq_handler):
    def login_required_towrap(function=None):
        http_login_required = login_required_orig(function)
        def decorate(request, *args, **kwargs):  # request is explicit here.
            if isinstance(request, XmppRequest):  # ! XXX: request.is_xmpp()
                if request.user.is_authenticated():
                    return function(request, *args, **kwargs)
                else:
                    return xmpp_unreg_view(request, function,
                      *args, **kwargs)
            else:  # Not XMPP. use original decorated.
                return http_login_required(request, *args, **kwargs)
        return decorate
    return login_required_towrap
login_required = get_login_required_wrapper()


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
    if isinstance(req, XmppRequest):  # ! TODO: request.is_xmpp()?
        return XmppResponse(msg)
    else:  # HTTP / redirect to reverse of view.
        return HttpResponseRedirect(reverse(*args, **kwargs))

