from django.conf.urls.defaults import *
from views import *
import xmppbase

# ? Should use a endline matching? Customizable, anyway.
# Note: endline matching never matches multiline messages.

cmdpatterns = patterns('',
    (r'^(?i)h(?:elp)? ?(?P<subject>.+)?$', xmpp_get_help, {}, 'snapboard_xmpp_help'),
    (r'^(?i)who(?:ami)?$', xmppbase.direct_to_template, {'template': 'snapboard/whoami.xmpp'}),
    (r'^REG(ISTER)?( +(?P<nickname>.+?) +(-p (?P<password>.+))?)?$', xmpp_register_cmd, {}, 'snapboard_xmpp_register_cmd'),
    (r'^[#!](?P<thread_id>\d+)$', thread, {}, 'snapboard_thread'),
    (r'^[#!]( (?P<num_limit>\d+)?( (?P<num_start>\d+)?)?)?$', \
      thread_index, {}, 'snapboard_thread_index'),  # spaces!
    (r'^[#!]c(?P<cat_id>\d+)$', category_thread_index, {},
      'category_thread_index'),
    (r'^[#!]c(?P<cat_id>\d+) (?P<POST_subject>.+?)\n(?P<POST_post>.(.*\n?)+)',
      new_thread, {}, 'snapboard_new_thread'),
#    (r'^#(?P<thread_id>\d+) (?P<POST_private>([^ ,]+?, )+?[^, ]+?)\n(?P<POST_post>(.*\n?)+)',
#      thread, {}, 'snapboard_thread'),  # Really just for testing.
    (r'^[#!](?P<thread_id>\d*)/(?P<parent_id>\d+) (?P<POST_post>(.*\n?)+)',
      post_reply, {}, 'snapboard_post_reply'),
    (r'^r( ([#!](?P<post_id>\d*))?( (?P<resource>.+)?)?)?$',
      xmppresourcify, {}, 'snapboard_xmppresourcify'),
    (r'^w( ([#!](?P<post_id>\d*))?( (?P<resource>.+)?)?)?$',
      r_watch_post, {}, 'snapboard_watchpost'),
)
