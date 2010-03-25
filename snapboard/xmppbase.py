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
import re  # Stripping XHTML images.

import sys

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
    def __init__(self, html=None, body=None, src=None, dst=None, id=None,
      user=None):
        # Current default is to create XHTML-message and construct plaintext
        # message from it.
        self.setuser(user)  # For minding the usersettings.
        if html is not None:
            self.setxhtml(html)
            # ! Don't usually allow to set both body and html.
        elif body is not None:
            self['body'] = body
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
        # Defaults here apply to AnonymousUsers, in particular.
        self.user = user
        self.u_disable_xmpp_xhtml = False
        self.u_disable_xmpp_images = True
        if hasattr(user, "sb_usersettings"):
            self.u_disable_xmpp_xhtml = \
              user.sb_usersettings.disable_xmpp_xhtml
            self.u_disable_xmpp_images = \
              user.sb_usersettings.disable_xmpp_images
        
    def setxhtml(self, html):
        # Usersettings are considered here
        # ! Note that changing user afterwards wouldn't change this.
        if not(self.u_disable_xmpp_xhtml):
            if (self.u_disable_xmpp_images):
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
          django.utils.html.strip_tags(self.imgfix(html)))
          
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
        return img_tag_re.sub(lambda x: img_repr(x.groups()[0]), htmlsource);
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
    except:
        request = None
        IsXmpp = False
    if IsXmpp:
        args = (args[0] + '.xmpp',) + args[1:]  # Fix template name.
        # Return some XmppResponse with rendered template.
        return XmppResponse(django.template.loader.render_to_string(*args, **kwargs), user=request.user)
    else:
        # Not Xmpp. Not our business.
        args = (args[0] + '.html',) + args[1:]  # ...
        return render_to_response_orig(*args, **kwargs)
