from django.conf.urls.defaults import *
from views import *

# ? Should use a endline matching? Customizable, anyway.
# Note: endline matching never matches multiline messages.

cmdpatterns = patterns('',
    (r'^HELP ?(?P<subject>.+)?$', xmpp_get_help, {}, 'snapboard_xmpp_help'),
    (r'^#(?P<thread_id>\d+)$', thread, {}, 'snapboard_thread'),
    (r'^#( (?P<num_limit>\d+)?( (?P<num_start>\d+)?)?)?', \
      thread_index, {}, 'snapboard_thread_index'),  # spaces!
)
