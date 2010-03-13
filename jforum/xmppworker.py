from django.core.management import setup_environ
import settings
setup_environ(settings)

from snapboard.xmppface import *

from multiprocessing import current_process


def worker(inqueue, outqueue):
    # ? ...Got better ideas for forcing loading?  It demises the
    # abstractness of this function!
    tmpo = XmppRequest("nonexistent")
    del(tmpo)
    while True:
        z = inqueue.get()
        if z == "QUIT":
            print("Process %r: received QUIT." % current_process())
            return
        result=processcmd(**z)
        outqueue.put(result)
