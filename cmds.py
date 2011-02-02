
from django.conf.urls.defaults import patterns, include

cmdpatterns = patterns('',
  ('', include('snapboard.cmds')),
)
