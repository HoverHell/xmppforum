
from django.conf.urls.defaults import patterns

# Note: `include` does not work well for cmdpatterns, so using this weird
# construction instead:

from xmppface.util import RegexCmdResolver

cmdpatterns = patterns('',
  RegexCmdResolver('', 'snapboard.cmds'),
)
