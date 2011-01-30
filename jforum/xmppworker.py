
def worker(inqueue):
    # loading happens after the start.
    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

    import snapboard.xmppface
    reload(snapboard.xmppface)  # ! Support deep reloading...

    from multiprocessing import current_process
    from sys import stderr

    # ? ...Got better ideas for forcing loading?  It demises the
    # abstractness of this function!
    tmpo = snapboard.xmppface.XmppRequest("nonexistent")
    del(tmpo)
    
    while True:
        z = inqueue.get()
        if z == "QUIT":
            print("Process %r: received QUIT." % current_process())
            return
        snapboard.xmppface.processcmd(**z)
