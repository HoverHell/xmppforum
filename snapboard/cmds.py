""" django-xmppface command patterns for the XMPP interface of the forum.
"""

# pylint: disable=C0103,W0401,W0614
# 'cmdpatterns' is preferrable, and importing * is more clean visually.

from django.conf.urls.defaults import patterns
from snapboard.views import *
from xmppface.xmppbase import direct_to_template


## Double id support, way 1: complex regexes.
from snapboard.models import Post
post_id_re = Post.id_m_re
post_id_re_f = r'(?P<post_form_id>' + Post.id_m_re_f + r')'
cmd_tag = r'[#!]'

### XMPP-pagination stuff: x_ipp - items per page (optional).
## NOTE: enclosed as a whole in the unnamed group to be able to do
##  `...nate_re + '?' + ...`
## FAIL: can't define x_page twice.
#xmpppaginate_re = r'(?:(?P<x_ipp>\d+) (?P<x_page>\d+)|(?P<x_page>\d+))'
xmpppaginate_re = r'(?:/(?:(?P<x_ipp>\d+)/)?(?P<x_page>\d+))'

## Make a regexp (for command-word) with optional short form.
cmd_word = lambda x, l=1: r'(?i)%s(?:%s)' % (x[:l], x[l:])

## Double id suport, way 2: decorators.
from snapboard.util import postid_to_id

# ? Should use a endline matching? Customizable, anyway.
# Note: endline matching never matches multiline messages.

cmdpatterns = patterns('',
    ## XMPP-specific.
    (r'^(?i)h(?:elp)? ?(?P<subject>.+)?$',
      xmpp_get_help, {}, 'snapboard_xmpp_help'),
    (r'^(?i)who(?:ami)?$',
      direct_to_template,
      {'template': 'snapboard/whoami.xmpp'}),

    ## Main indexes.
    (r'^' + cmd_word('last') + cmd_tag +
      '(?P<thread_id>\d+)l(?: (?P<num_posts>\d+))?$',
      thread_latest, {}, 'snapboard_thread_latest'),
    (r'^' + cmd_tag + xmpppaginate_re + '?$',
      thread_index, {}, 'snapboard_thread_index'),
    (r'^/$', category_index, {}, 'snapboard_category_index'),
    (r'^/(?P<cat_id>[^/]+)$',
      category_thread_index, {}, 'category_thread_index'),

    (r'^/(?P<POST_category>[^/ ]+) (?P<POST_subject>.+?)\n(?P<POST_text>.(.*\n?)+)',
      new_thread, {}, 'snapboard_new_thread'),
    # TODO: edit_settings?

    (r'^' + cmd_tag + post_id_re_f + '$',
      thread_post, {}, 'snapboard_thread_post'),
    ## XXX: The '[^ ]' there is to avoid mess between '# 10' and '#  10'
    #(r'^' + cmd_tag + post_id_re_f + r'? (?P<POST_text>[^ ](.*\n?)+)',
    #  post_reply, {}, 'snapboard_post_reply'),
    (r'^' + cmd_tag + post_id_re_f + r'? (?P<POST_text>(.*\n?)+)',
      post_reply, {}, 'snapboard_post_reply'),
    (r'^' + cmd_word('edit') + cmd_tag +
      '?(?: ' + post_id_re_f + r'?(?: (?P<POST_text>(.*\n?)+))?)?',
      edit_post, {}, 'snapboard_edit_post'),
    (r'^r(?: ' + post_id_re_f + r'?(?: +(?P<resource>.+)?)?)?$',
      xmppresourcify, {}, 'snapboard_xmppresourcify'),  # XMPP-specific.
    # TODO: show_revisions?
    # TODO: watchlist?
    (r'^w( ' + post_id_re_f + r'?( (?P<resource>.+)?)?)?$',
      r_watch_post, {}, 'snapboard_watchpost'),
    (r'^!delthread (?P<thread_id>\d+)$',
      r_removethread, {}, 'snapboard_remove_thread'),
    # Togglers.
    (r'^!gsticky (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_gsticky, {}, 'snapboard_set_gsticky'),
    (r'^!csticky (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_csticky, {}, 'snapboard_set_csticky'),
    (r'^!close (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_close, {}, 'snapboard_set_close'),
    (r'^!censor ' + post_id_re_f + r'(?: (?P<state>1|0))?$',
      postid_to_id(r_set_censor, paramname='oid'),
      {}, 'snapboard_set_censor'),  # post id with '#'.
)
