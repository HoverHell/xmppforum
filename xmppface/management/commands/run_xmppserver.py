#!/usr/bin/env python
"""
# TODO
"""

#from twisted.words.protocols.jabber import component
from twisted.internet import reactor
from django.conf import settings
from django.core.management.base import NoArgsCommand
from twisted.application.app import startApplication

##from ossignal import install_shutdown_handlers
#from transport import main

# ! XXX: bleh. naming.
#from xmppface.jaboardxmpp import application

# ? XXX: logging? It is set up both in settings and in twisted, but what's
# actually needed?

import sys

## Argument possibilities:
## * Can override create_parser of the BaseCommand to just return some part
##  of sys.argv
## * Can add few necessary options (like `-l`. see
##  twisted.application.app.ServerOptions.optParameters).

class Command(NoArgsCommand):
    def handle_noargs(self, *args, **options):
        ## ! XXX: `from django.utils import autoreload`?  Might put it into
        ## xmppface or xmppwoker
        from xmppface.s2scfg import cfg_override
        from xmppface.s2sbase import setup_twisted_app
        application = setup_twisted_app(cfg_override(settings))
        startApplication(application, False)
        reactor.run()

        """
                                         "tcp:%s:%s" % (host, port))
        c.setServiceParent(connector)
        connector.startService()
        #install_shutdown_handlers(c.shuttingDown)
        reactor.run() #installSignalHandlers=False)
        """