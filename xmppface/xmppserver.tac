""" twistd-standalone file for starting up a XMPP S2S server. """

import settings  # use manage command instead if this doesn't work

from xmppface.s2scfg import cfg_override
from xmppface import s2sbase

application = s2sbase.setup_twisted_app(cfg_override(settings))
