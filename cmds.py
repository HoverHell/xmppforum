
from django.conf.urls.defaults import patterns

# Note: `include` does not work well for cmdpatterns, so using this weird
# construction instead:

from xmppface.util import RegexCmdResolver

cmdpatterns = patterns('',
  RegexCmdResolver('', 'xmppface.cmds'),  # The default useful stuff.
  RegexCmdResolver('', 'snapboard.cmds'),  # App-specific stuff.
)
