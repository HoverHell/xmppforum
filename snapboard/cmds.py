""" django-xmppface command patterns for the XMPP interface of the forum.
"""

# pylint: disable=C0103,W0401,W0614
# 'cmdpatterns' is preferrable, and importing * is more clean visually.

from django.conf.urls.defaults import patterns
from snapboard.views import *
from xmppface.xmppbase import direct_to_template

# ? Should use a endline matching? Customizable, anyway.
# Note: endline matching never matches multiline messages.

cmdpatterns = patterns('',
    (r'^(?i)h(?:elp)? ?(?P<subject>.+)?$',
      xmpp_get_help, {}, 'snapboard_xmpp_help'),
    (r'^(?i)who(?:ami)?$',
      direct_to_template,
      {'template': 'snapboard/whoami.xmpp'}),
    (r'^(?i)reg(?:ister)?( +(?P<nickname>.+?)( +-p (?P<password>.+))?)?$',
      xmpp_register_cmd, {}, 'snapboard_xmpp_register_cmd'),
    (r'^(?i)unregister!$',
      xmpp_unregister_cmd, {}, 'snapboard_xmpp_unregister_cmd'),
    (r'^(?i)log(?:in)?$',
      xmpp_web_login_cmd, {}, 'snapboard_xmpp_login_cmd'),
    (r'^(?i)password( (?P<password>.+))?$',
      xmpp_web_changepw, {}, 'snapboard_xmpp_changepw'),
    (r'^[#!](?P<thread_id>\d+)$', thread, {}, 'snapboard_thread'),

    (r'^[#!]c$', category_index, {}, 'snapboard_category_index'),
    (r'^!delthread (?P<thread_id>\d+)$',
      r_removethread, {}, 'snapboard_remove_thread'),
    # Togglers.
    (r'^!gsticky (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_gsticky, {}, 'snapboard_set_gsticky'),
    (r'^!csticky (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_csticky, {}, 'snapboard_set_csticky'),
    (r'^!close (?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_close, {}, 'snapboard_set_close'),
    (r'^!censor [!#](?P<oid>\d+)(?: (?P<state>1|0))?$',
      r_set_censor, {}, 'snapboard_set_censor'),  # post id with '#'.


    (r'^[#!]c(?P<cat_id>\d+)$',
      category_thread_index, {}, 'category_thread_index'),
    (r'^[#!]( (?P<num_limit>\d+)?( (?P<num_start>\d+)?)?)?$',
      thread_index, {}, 'snapboard_thread_index'),  # spaces!
    (r'^[#!]c(?P<cat_id>\d+) (?P<POST_subject>.+?)\n(?P<POST_post>.(.*\n?)+)',
      new_thread, {}, 'snapboard_new_thread'),
    (r'^[#!](?P<thread_id>\d*)/(?P<parent_id>\d+) (?P<POST_post>(.*\n?)+)',
      post_reply, {}, 'snapboard_post_reply'),
    (r'^r( ([#!](?P<post_id>\d*))?( (?P<resource>.+)?)?)?$',
      xmppresourcify, {}, 'snapboard_xmppresourcify'),
    (r'^w( ([#!](?P<post_id>\d*))?( (?P<resource>.+)?)?)?$',
      r_watch_post, {}, 'snapboard_watchpost'),
)
