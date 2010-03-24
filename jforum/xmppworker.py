from django.core.management import setup_environ
import settings
setup_environ(settings)

# outqueue
outqueueaddr = settings.SOCKET_ADDRESS
import socket

import snapboard.xmppface
reload(snapboard.xmppface)  # Support deep reloading...

from multiprocessing import current_process
from sys import stderr


def worker(inqueue):
    # ? ...Got better ideas for forcing loading?  It demises the
    # abstractness of this function!
    tmpo = snapboard.xmppface.XmppRequest("nonexistent")
    del(tmpo)
    
    outqueue = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    outqueue.connect(outqueueaddr)
    
    while True:
        z = inqueue.get()
        if z == "QUIT":
            print("Process %r: received QUIT." % current_process())
            return
        result = snapboard.xmppface.processcmd(**z)
        # We expect it to be a dict with specific fields.
        stderr.write("\nResult type %r: %r." % (type(result), result))
        outqueue.send(str(result))  # It decides itself on how to be dumped.
