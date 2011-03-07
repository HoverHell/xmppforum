# -*- coding: utf-8 -*-

from time import mktime

from django import template
from django.conf import settings

from snapboard.templatetags.textile import textile
from snapboard.templatetags import markdown
from snapboard.templatetags import bbcode

register = template.Library()


register.filter('textile', textile)


@register.filter
def post_summary(value, arg):
    """ Returns the first N characters of a block of text where N is the
    only argument.  """
    l = int(arg)
    if len(value) >= arg:
        return value
    else:
        return value[:l] + '...'


@register.filter(name='markdown')
def markdown_filter(value, arg=''):
    extensions=arg.split(",")
    if len(extensions) == 1 and extensions[0] == '':
        # if we don't do this, no arguments will generate critical warnings
        # in markdown
        extensions = []
        safe_mode = False
    elif len(extensions) > 0 and extensions[0] == "safe":
        extensions = extensions[1:]
        safe_mode = True
    else:
        safe_mode = False

    return markdown.markdown(value, extensions, safe_mode=safe_mode)


@register.filter(name='bbcode')
def bbcode_filter(value, arg=''):
    return bbcode.bb2xhtml(value, True)


snap_filter = getattr(settings, 'SNAP_POST_FILTER', 'bbcode').lower()
if snap_filter == 'bbcode':
    render_filter = bbcode_filter
elif snap_filter == 'textile':
    render_filter = lambda text, arg: textile(text)
else:
    render_filter = markdown_filter
register.filter('render_post', render_filter)


@register.filter
def timestamp(dt):
    """ Returns a timestamp usable by JavaScript from a datetime.  """
    try:
        return str(int(1000*mktime(dt.timetuple())))
    except:
        return u''


import time
import datetime
from snapboard.util import format_timedelta
class RelTimeNode(template.Node):
    """ A template tag for printing relative-readable-formatted time from
    the given date.  """
    def __init__(self, p_ndate):
        self.ndate = template.Variable(p_ndate)

    def render(self, context):
        now = context.get('now', None)
        if now is None:
            # Should never appen if template context processor
            # is providing it.
            now = time.mktime(datetime.datetime.now().timetuple())
            context['now'] = now
        try:
            ndate = self.ndate.resolve(context)
        except template.VariableDoesNotExist:
            return u''
        if not isinstance(ndate, datetime.datetime):
            return (u'?sometime?')
        return format_timedelta(now - time.mktime(ndate.timetuple()))


@register.tag
def reltime(parser, token):
    args = token.split_contents()
    if len(args) == 2:
        return RelTimeNode(args[1])
    else:
        raise template.TemplateSyntaxError


## Avatar-reworked.
from avatar.templatetags import avatar_tags
from avatar import util as avatar_util
from avatar.settings import (AVATAR_DEFAULT_SIZE, AVATAR_DEFAULT_URL,
  AVATAR_GRAVATAR_BACKUP)
get_primary_avatar_c = \
  avatar_util.cache_result(avatar_util.get_primary_avatar)

def _make_av_tag(url, **kwa):
    """ Renders an actual <img/> tag for avatar_opt.
    All parameters are added to the tag unless their value is empty (thus no
    empty parameter can be included.  """
    ## kwa's join has space prepended if any items are there.
    return u'<img src="%s"%s />' % (
      url,
      u''.join(
        [u' %s="%s"' % (k[2:], v) \
          for k, v in kwa.iteritems() \
          if (v and k.startswith('t_'))]),
      )


if not (AVATAR_DEFAULT_URL or AVATAR_GRAVATAR_BACKUP):
    def _in_avatar_opt(user, sizef=None, **kwa):
        """ Internal avatar_opt function: returns nothing if there's no
        avatar.  """
        size = sizef if sizef is not None else AVATAR_DEFAULT_SIZE
        avatar = get_primary_avatar_c(user, sizef)
        if not avatar:
            return u''  # no tag at all.
        url = avatar.avatar_url(size)
        return _make_av_tag(url, **kwa)
          
else:
    def _in_avatar_opt(user, size, **kwa):
        """ Internal avatar_opt function: wraps avatar_url with custom img
        tag.  """
        url = avatar_tags.avatar_url(user, size)
        return _make_av_tag(url, **kwa)

@register.simple_tag
def avatar_opt(user, size=AVATAR_DEFAULT_SIZE, t_class=""):
    """ Customized avatar templatetag.
    Can be used as {% avatar_opt user None "" %}.  """
    ## v1: hack-ish.
    #aurl = avatar_tags.avatar_url(user, size)
    #if aurl == MEDIA_URL:
    #    return u''
    #return avatar_utils.avatar_url(user, size)
    #size = sizef if sizef is not None else AVATAR_DEFAULT_SIZE
    return _in_avatar_opt(user, size, t_class=t_class)
