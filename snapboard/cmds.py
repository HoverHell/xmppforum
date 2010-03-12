from django.conf.urls.defaults import *
from views import *

# ? Should use a endline matching? Customizable, anyway.

cmdpatterns = patterns('',
    (r'^#(?P<thread_id>\d+)$', thread, {}, 'snapboard_thread'),
    (r'^#( (?P<num_limit>\d+)?( (?P<num_start>\d+)?)?)?', \
      thread_index, {}, 'snapboard_thread_index'), # spaces!
)
