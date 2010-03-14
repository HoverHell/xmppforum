from django.core.management import setup_environ
import settings
setup_environ(settings)


import snapboard.xmppface

# gets worse
reload(snapboard.xmppface)

from multiprocessing import current_process
import sys


def worker(inqueue, outqueue):
    # ? ...Got better ideas for forcing loading?  It demises the
    # abstractness of this function!
    tmpo = snapboard.xmppface.XmppRequest("nonexistent")
    del(tmpo)
    while True:
        z = inqueue.get()
        if z == "QUIT":
            print("Process %r: received QUIT." % current_process())
            return
        result=snapboard.xmppface.processcmd(**z)
        sys.stderr.write("\bResult is of type %r." % type(result))
        sys.stderr.write("  ...and is %r.\n" % str(result))
        outqueue.put(result)
