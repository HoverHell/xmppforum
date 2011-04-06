""" django-xmppface command patterns for the XMPP interface of the forum.
"""

# pylint: disable=C0103,W0401,W0614
# 'cmdpatterns' is preferrable, and importing * is more clean visually.

from django.conf.urls.defaults import patterns
from snapboard.views import *
from xmppface.xmppbase import direct_to_template


## Double id support, way 1: complex regexes.
from snapboard.models import Post
post_id_re = Post.id_m_re_f
post_id_re_f = r'(?P<post_form_id>' + post_id_re + r')'

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
    (r'^[#!](?P<thread_id>\d+)$', thread, {}, 'snapboard_thread'),
    # TODO: thread_post?
    (r'^[#!](?P<thread_id>\d+)l(?: (?P<num_posts>\d+))?$',
      thread_latest, {}, 'snapboard_thread_latest'),
    (r'^[#!]( (?P<num_limit>\d+)?( (?P<num_start>\d+)?)?)?$',
      thread_index, {}, 'snapboard_thread_index'),  # spaces!
    (r'^[#!]c$', category_index, {}, 'snapboard_category_index'),
    (r'^[#!]c(?P<cat_id>\d+)$',
      category_thread_index, {}, 'category_thread_index'),

    (r'^[#!]c(?P<POST_category>\d+) (?P<POST_subject>.+?)\n(?P<POST_text>.(.*\n?)+)',
      new_thread, {}, 'snapboard_new_thread'),
    # TODO: edit_settings?

    (r'^[#!]' + post_id_re_f + r'? (?P<POST_text>(.*\n?)+)',
      post_reply, {}, 'snapboard_post_reply'),
    (r'^[#!]e(?: ' + post_id_re_f + r'?(?: (?P<POST_text>(.*\n?)+))?)?',
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
