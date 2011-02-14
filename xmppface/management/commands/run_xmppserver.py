#!/usr/bin/env python
"""
# TODO
"""

from twisted.internet import reactor
from django.conf import settings
from django.core.management.base import NoArgsCommand
from twisted.application.app import startApplication

##from ossignal import install_shutdown_handlers

# ? XXX: logging? It is set up both in settings and in twisted, but what's
# actually needed?

import sys

## Arguments?

class Command(NoArgsCommand):
    def handle_noargs(self, *args, **options):
        ## ! XXX: `from django.utils import autoreload`?  Might put it into
        ## xmppface or xmppwoker
        from xmppface.s2scfg import cfg_override
        from xmppface.s2sbase import setup_twisted_app
        application = setup_twisted_app(cfg_override(settings))
        startApplication(application, False)
        reactor.run()
