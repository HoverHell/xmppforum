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
XMPPOUTQUEUEADDR = getattr(settings, 'SOCKET_ADDRESS', 'xmppoutqueue')
import socket
import time  # periodic reconnect attempts
import copy
from thread import start_new_thread  # for reconnector thread


# for XmppResponse

# For render_to_response wrapper
from django.shortcuts import render_to_response as render_to_response_orig

# for login_required wrapper
from django.contrib.auth.decorators import login_required as login_required_orig

# For success_or_reverse_redirect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect


import re  # Stripping XHTML images.

# django uses best json available
from django.utils import simplejson # For serialization of XmppResponse


class XmppRequest(object):
    """
     XmppRequest is a class partially compatible with HttpRequest, so it can
     be used as a request variable in the views.

     It doesn't provide most of the data now, though, so using it now with
     html templates is not only wrong but also impossible.
    """
    def __init__(self, srcjid):
        import models
        # This isn't really meant for anything yet.
        self.srcjid = srcjid
        # "Authentication":
        try:
            self.user = models.User.objects.get(sb_usersettings__jid__exact=srcjid)
        except models.User.DoesNotExist:
            self.user = models.AnonymousUser()
        # Populating extra fields:
        self.META = {'REMOTE_ADDR': srcjid}
        self.POST = {}
        self.GET = {}
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
        self['class'] = 'message'
        # Current default is to create XHTML-message and construct plaintext
        # message from it.
        self.setuser(user)
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

    def setuser(self, user=None):
        import models
        self.user = user or models.AnonymousUser()
        self.usersettings = self.user.get_user_settings()

    def setxhtml(self, html):
        # Usersettings are considered here
        # ! Note that changing user afterwards wouldn't change this.
        if not(self.usersettings.disable_xmpp_xhtml):
            if (self.usersettings.disable_xmpp_images):
                self['html'] = self.imgfix(html)
            else:
                self['html'] = html
        else:
            print " D: skipping HTML part on user's preferences."
        # Body is set forcibly for less possible confusion. Although, some
        # alteration is possible here.
        # Note: in Psi, non-XHTML body is used in displayed notifications.
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
            elif key in ('body', 'subject'):
                content = "<%s>%s</%s>"%(key, value, key) + content
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
<vCard xmlns="vcard-temp" version="2.0" prodid="-//HandGen//NONSGML vGen v1.0//EN"/></iq>
    """
    def __init__(self, type='get', **kwargs):
        """
        Should (usually) get 'src', 'dst', 'content', possibly 'id' in kwargs.
        """
        self['class'] = 'iq'
        self['type'] = type
        self.update(kwargs)  # src, dst, id, content, ...

    def __str__(self):
        """
        Serializes itself into string.
        """
        return simplejson.dumps(self)


class XmppPresence(dict):
    """
    XmppResponse-like object for XMPP presence messages.
    """
    """
    Example:
<presence from="hoverhell1@jabber.ru/hheee" xml:lang="en" to="hell@hell.orts.ru/hheee">
<show>chat</show><status>FFC? FFS!</status><priority>0</priority></presence>
    """
    def __init__(self, **kwargs):
        """
        Should (usually) get 'src', 'dst',
         and 'status', 'priority', 'show' (or 'content') in kwargs.
        """
        self['class'] = 'presence'
        self.update(kwargs)

    def __str__(self):
        """
        Serializes itself into string.
        """
        selfrepr = {}
        content = ''
        for key, value in self.iteritems():
          if key in ('show', 'status', 'priority'):
              content = "<%s>%s</%s>"%(key, value, key) + content
          else:
            selfrepr[key] = value
        selfrepr['content'] = content
        return simplejson.dumps(selfrepr)

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
    connecting = True
    # ! AF_UNIX socket is currently used.
    #xmppoutqueue = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sys.stderr.write(" D: connecting to the xmppoutqueue...\n")
    xmppoutqueue = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    pause = 0.5  # current time to wait until retry
    pause_max = 4.0  # somewhat-around-maximum waiting time.
    while True:
        try:
            xmppoutqueue.connect(XMPPOUTQUEUEADDR)
        except:
            if pause < pause_max:
                sys.stderr.write(" ERROR: could not connect to "
                 "xmppoutqueue! Waiting for %s seconds.\n" % pause)
            elif abs(pause_max - pause) < 0.5:  # got to max.
                sys.stderr.write(" ERROR: could not connect to "
                 "xmppoutqueue! Will keep trying.\n")
                pause += 1
            time.sleep(pause)
            if pause < pause_max:
                pause *= 2  # wait 8 seconds at most, doubling on attempt.
            continue  # try again
        sys.stderr.write(" D: connected to the xmppoutqueue.\n")
        connecting = False
        processing = copy.copy(unsent)
        unsent = []
        for msg in processing:
            send_xmpp_message(msg)
        break  # success.
start_new_thread(connkeeper, ())

def send_xmpp_message(msg):
    """
    Common function to send a XMPP message through running XMPP connection
    provider. Should generally be called with XmppResponse argument with all
    necessary fields set.
    """
    # It uses global pre-initialized xmppoutqueue connection.
    try:
        # msg decides itself on how to be dumped.
        # And newline is used to split socket datastream into separate
        # messages.
        xmppoutqueue.send(str(msg)+"\n")
    except:  # ! Should do more reliability increasing here.
        sys.stderr.write(" ERROR: Could not write to xmppoutqueue! (reconnecting...)\n")
        sys.stderr.write("    Message was: %s.\n" % str(msg))
        unsent.append(msg)
        if not connecting:
            xmppoutqueue.close()
            start_new_thread(connkeeper(), ())
        

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
                return function(request, *args, **kwargs)
            else:
                pass  # ! Access denied and offer registration here.
        else:  # Not XMPP. use original decorated.
            return http_login_required(request, *args, **kwargs)
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

