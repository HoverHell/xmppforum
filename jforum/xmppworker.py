from django.core.management import setup_environ
import settings
setup_environ(settings)

import snapboard.xmppface
reload(snapboard.xmppface)  # ! Support deep reloading...
from snapboard.xmppbase import send_xmpp_message

from multiprocessing import current_process
from sys import stderr


def worker(inqueue):
    # ? ...Got better ideas for forcing loading?  It demises the
    # abstractness of this function!
    tmpo = snapboard.xmppface.XmppRequest("nonexistent")
    del(tmpo)
    
    while True:
        z = inqueue.get()
        if z == "QUIT":
            print("Process %r: received QUIT." % current_process())
            return
        result = snapboard.xmppface.processcmd(**z)
        stderr.write("\nResult type %r: %r." % (type(result), result))
        if result:  # Actually, may prefer to move that away.
            send_xmpp_message(result)
        else:
            stderr.write("\nResult is empty. Ignoring.\n");
