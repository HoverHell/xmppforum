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
        return format_timedelta(now - time.mktime(ndate.timetuple()))


@register.tag
def reltime(parser, token):
    args = token.split_contents()
    if len(args) == 2:
        return RelTimeNode(args[1])
    else:
        raise template.TemplateSyntaxError
