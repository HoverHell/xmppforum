""" A jaboard XMPP face server as a standalone server via s2s.  """

from twisted.application import service, strports
from twisted.internet import protocol
from twisted.words.xish import domish  # For creating messages to send.
from wokkel import component, server, xmppim
import sys


# Try to use django to get best available json library (for decoding IPC
# data).
try:
    from django.utils import simplejson
except ImportError:  # No Django? Well, we're abstract enough.
    import simplejson

import traceback  # Debug on exceptions.

from multiprocessing import Process, Queue
from Queue import Empty
from thread import start_new_thread
import signal  # Sig handlers.
import time  # Old processes killing timeout.

CFG = {
  'DOMAIN': 'bot.example.org',
  'LOG_TRAFFIC': True,
  'NWORKERS': 2,
  'S2S_PORT': 'tcp:5269:interface=0.0.0.0',
  'SECRET': 'secret',
  'SOCKET_ADDRESS': 'xmppoutqueue',
}

import settings  # XXX: not nice non-overridable way.


def cfg_override(cfg, settings_module):
    """ Grab whatever was overriden in settings. """
    for key, val in cfg.iteritems():
        cfg[key] = getattr(settings_module, key, val)
    return cfg

CFG = cfg_override(CFG, settings)
g_workerlist, g_inquque = None, None


def worker(w_inqueue):
    """ multiprocessing worker that grabs tasks (requests) from queue and
    gives them to the xmppface layer. """
    # loading happens after the start.
    from multiprocessing import current_process
    curproc = "Process %r" % current_process()
    print "%s: starting."

    from django.core.management import setup_environ
    import settings
    setup_environ(settings)

    from . import xmppface
    try:
        while True:
            print "%s: waiting for stuff to process."
            data = w_inqueue.get()
            if data == "QUIT":
                # ? Which logging to use?
                print "%s: received QUIT." % curproc
                return
            xmppface.processcmd(data)
    except KeyboardInterrupt:
        print "%s: Interrupted; finishing." % curproc
        return


def createworkerpool(targetfunc, nworkers):
    """ Creates nworkers of workers, running func.
    func should take (inqueue, ) as arguments.
    Returns tuple (workerlist, inqueue). """
    inqueue = Queue()
    workerlist = []
    for i in xrange(nworkers):  # pylint: disable-msg=W0612
        new_worker = Process(target=targetfunc, args=(inqueue, ))
        new_worker.start()
        workerlist.append(new_worker)
    return (workerlist, inqueue)


def finishworkersgracefully(workerlist, inqueue):
    """ Tell workers to quit, or kill them if they don't. """
    for i in xrange(len(workerlist) + 1):  # pylint: disable-msg=W0612
        # (+1 for certainty)
        inqueue.put_nowait("QUIT")
    time.sleep(0.3)
    waitforkill = False
    for workprc in workerlist:  # Anyone still alive?
        if workprc.is_alive():
            waitforkill = True
            break
    # Does that do something?
    inqueue.close()
    inqueue.join_thread()
    if not waitforkill:
        return
    # Still someone to kill. Wait and terminate.
    server.log.err(" Waiting before killing remaining processes. ")
    time.sleep(3)  # If some still live - we've got some serious problems.
    for workprc in workerlist:
        if workprc.is_alive():
            server.log.err(" ------- W: finishworkersgracefully: killing " \
             "still-alive worker %r." % workprc)
            workprc.terminate()
        del(workprc)


# pylint: disable-msg=W0613
# :W0613: *Unused argument %r*
# pylint: disable-msg=W0703
# :W0703: *Catch "Exception"*
def sighuphandler(signum, frame):
    """ Live reloading of workers without stopping the XMPP part. Might be
    unnecessary after all. """
    # Shouldn't be executed in child processes, btw.
    global g_inqueue, g_workerlist  # pylint: disable-msg=W0603
    # :W0603: *Using the global statement*
    import xmppworker
    try:
        reload(xmppworker)
    except Exception:
        server.log.err(" -------------- E: Reload FAILED.")
        traceback.print_exc()
        return
    inqueueold, workerlistold = g_inqueue, g_workerlist
    g_workerlist, g_inqueue = createworkerpool(xmppworker.worker,
      CFG['NWORKERS'])
    while not inqueueold.empty():
        # put possible remaining requests into the new queue
        try:
            old_task = inqueueold.get_nowait()
            g_inqueue.put_nowait(old_task)
        except Empty:
            break
    start_new_thread(finishworkersgracefully, (workerlistold, inqueueold))
#signal.signal(signal.SIGHUP, sighuphandler)


def sigqhandler(signum, frame):
    """ Kill gracefully on quit-signals."""
    sys.stderr.write(" XX: sigtermed. ")
    try:
        finishworkersgracefully(g_workerlist, g_inqueue)
    except Exception, e:
        traceback.print_exc()


#signal.signal(signal.SIGTERM, sigqhandler)
#signal.signal(signal.SIGINT, sigqhandler)


# pylint: disable-msg=C0103
# *Invalid name "%s" (should match %s)*  - twisted legacy.
# pylint: disable-msg=W0201
# *Attribute %r defined outside __init__*
class AvailabilityPresenceX(xmppim.AvailabilityPresence):
    """ Slightly extended/fixed class that saves <x> element from the
    presence stanze.  """
    childParsers = {
      ## Those shoulb be 'accumulated' from AvailabilityPresence:
      #(None, 'show'): '_childParser_show',
      #(None, 'status'): '_childParser_status',
      #(None, 'priority'): '_childParser_priority',
      ('vcard-temp:x:update', 'x'): '_childParser_photo',
    }

    def _childParser_photo(self, element):
        """ Adds the 'photo' data if such element exists. """
        self.photo = None
        for child in element.elements():  # usually only one.
            if child.name == 'photo':
                if child.children:
                    self.photo = child.children[0]
                else:
                    self.photo = ""


# Protocol handlers
# pylint: disable-msg=R0904
# :R0904: *Too many public methods (%s/%s)*  - twisted legacy.
class PresenceHandler(xmppim.PresenceProtocol):
    """ Presence XMPP subprotocol - accept+relay handler.

    This handler blindly accepts incoming presence subscription requests,
    confirms unsubscription requests and responds to presence probes.

    Note that this handler does not remember any contacts, so it will not
    send presence when starting.
    """

    def __init__(self):
        """ Some data to store. """
        xmppim.PresenceProtocol.__init__(self)
        self.statustext = u"Greetings"
        self.subscribedto = {}
        # semi-hack to support vCard processing.:
        self.presenceTypeParserMap['available'] = AvailabilityPresenceX
        # ? Ask django-xmppface to ask self to send presences?

    def subscribedReceived(self, presence):
        """ Subscription approval confirmation was received. """
        server.log.msg(" ------- D: A: subscribedReceived.")
        g_inqueue.put_nowait({'auth': 'subscribed',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def unsubscribedReceived(self, presence):
        """ Unsubscription confirmation was received. """
        server.log.msg(" ------- D: A: unsubscribedReceived.")
        g_inqueue.put_nowait({'auth': 'unsubscribed',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def subscribeReceived(self, presence):
        """ Subscription request was received.
        Always grant permission to see our presence. """
        server.log.msg(" ------- D: A: subscribeReceived.")
        self.subscribed(recipient=presence.sender,
                        sender=presence.recipient)
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)
        # Ask for subscription in turn.
        # ? Need some extracheckings for that?
        server.log.msg(" ------- D: A: Requesting mutual subscription... ")
        self.subscribe(recipient=presence.sender,
                       sender=presence.recipient)
        g_inqueue.put_nowait({'auth': 'subscribe',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def unsubscribeReceived(self, presence):
        """ Unsubscription request was received.
        Always confirm unsubscription requests. """
        server.log.msg(" ------- D: A: unsubscribeReceived.")
        self.unsubscribed(recipient=presence.sender,
                          sender=presence.recipient)
        g_inqueue.put_nowait({'auth': 'unsubscribe',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def availableReceived(self, presence):
        """ Available presence was received. """
        server.log.msg(" ------- D: A: availableReceived. show: %r" % (
          presence.show,))
        show = presence.show or "online"
        g_inqueue.put_nowait({'stat': show,
           'photo': getattr(presence, 'photo', None),
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def unavailableReceived(self, presence):
        """ Unavailable presence was received. """
        server.log.msg(" ------- D: A: unavailableReceived.")
        g_inqueue.put_nowait({'stat': 'unavail',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def probeReceived(self, presence):
        """ A presence probe was received.
        Always send available presence to whoever is asking. """
        server.log.msg(" ------- D: A: probeReceived.")
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)


class MessageHandler(xmppim.MessageProtocol):
    """ Message XMPP subprotocol - relay handler. """

    def onMessage(self, message):
        """ A message stanza was received. """
        server.log.msg(" ------- D: A: onMessage.")

        # Ignore error messages
        if message.getAttribute('type') == 'error':
            server.log.msg(" -------------- D: W: error-type message.")
            return

        ## Note: possible types are 'chat' and no type (i.e. plain non-chat
        ## message).
        # ? But are there other types besides those and 'error' (and
        # 'headline?
        try:
            msgtype = message.getAttribute('type')
            if msgtype == 'headline':
                # ? Something interesting in those?
                # (see note2.txt for example)
                return  # ...or just skip them.
            if not (msgtype == 'chat'):
                # For now - log them.
                server.log.msg(" ------- !! D: message of type %r." % msgtype)

            # Dump all the interesting parts of data to the processing.
            g_inqueue.put_nowait(
              {'src': message.getAttribute('from'),
               'dst': message.getAttribute('to'),
               'body': message.body.children[0],
               'id': message.getAttribute('id'),
               'type': message.getAttribute('type'),
              })
        except Exception:
            # Something went pretty.wrong.
            server.log.err(" -------------- E: onMessage: exception.")
            traceback.print_exc()


## vCard support stuff.
try:
    # pylint: disable-msg=E0611,F0401
    # :E0611: *No name %r in module %r*  - d'uh.
    from twisted.words.protocols.xmlstream import XMPPHandler
except ImportError:
    from wokkel.subprotocols import XMPPHandler

VCARD_RESPONSE = "/iq[@type='result']/vCard[@xmlns='vcard-temp']"


class VCardHandler(XMPPHandler):
    """ Subprotocol handler that processes received vCard iq responses. """

    def connectionInitialized(self):
        """ Called when the XML stream has been initialized.
        Sets up an observer for incoming stuff. """
        self.xmlstream.addObserver(VCARD_RESPONSE, self.onVcard)

    # pylint: disable-msg=R0201
    # *Method could be a function* - should be overridable.
    def onVcard(self, iq):
        """ iq response with vCard data received """
        def _jparse(elem):
            """ Parses the provided XML element, returning recursed dict
            with its data (ignoring *some* text nodes).  """
            if not elem.firstChildElement():  # nowhere to recurse to.
                return unicode(elem)  # perhaps there's some string, then.
            outd = {}
            for child in elem.elements():  # * ignoring other text nodes,
                # * ...and overwriting same-name siblings, apparently.
                outd[child.name] = _jparse(child)
            return outd

        server.log.msg("onVcard. iq: %r" % iq)
        server.log.msg(" ... %r" % iq.children)
        el_vcard = iq.firstChildElement()
        if el_vcard:
            g_inqueue.put_nowait(
              {'src': iq.getAttribute('from'),
               'dst': iq.getAttribute('to'),
               'vcard': _jparse(el_vcard)})


class OutqueueHandler(protocol.Protocol):
    """ Relay for sending messages through the outqueue. """

    def __init__(self):
        pass

    def connectionMade(self):
        server.log.msg(" D: OutqueueHandler: connection received.\n")

    datatemp = ""  # for holding partially reveived data
    dataend = "\n"  # End character for splitting datastream.

    # pylint: disable-msg=R0201
    # *Method could be a function* - avoiding indent-hell here.
    def ProcessData(self, dataline):
        """ Called from dataReceived for an actual combined data ready for
        processing (which is determined by newlines in the stream,
        actually).  """
        try:
            x = simplejson.loads(dataline)
            server.log.msg(" ------- D: Got JSON line of length %d:" % (
              len(dataline)))
            # server.log.msg(" --    %r        --\n  " % x)
            if 'class' in x:
                response = domish.Element((None, x['class']))
                # Values are supposed to be always present here:
                response['to'] = x['dst']
                response['from'] = x['src']
                for extranode in ('type', 'xml:lang'):
                    if extranode in x:
                        response[extranode] = x[extranode]
                if 'content' in x:
                    # We're provided with raw content already.
                    # It is expected to be valid XML.
                    # (if not - remote server will probably drop the s2s
                    # connection)
                    ## ? Process it with BeautifulSoup? :)
                    response.addRawXml(x['content'])
                if x['class'] == 'message':
                    # Create and send a response.
                    response['type'] = response.getAttribute('type') \
                      or 'chat'
                # Everything else should be in place already for most types.
                # XXX: This throws some weird errors but works.
                msgHandler.send(response)
            else:  # not 'class'
                pass  # Nothing else implemented yet.
        except ValueError:
            server.log.err(" -------------- E: Failed processing: "
             "%r" % dataline)

    def dataReceived(self, data):
        # Process received data for messages to send.
        server.log.msg(u" ------- D: Received data (%r) of len %d with %d "
          "newlines." % (type(data), len(data), data.count("\n")))
        if self.dataend in data:  # final chunk.
            # Unlike splitlines(), this returns an empty string at the
            # end if data ends with newline.
            datas = data.split(self.dataend)
            self.ProcessData(self.datatemp + datas[0])
            for datachunk in datas[1:-1]:
                # suddenly, more complete messages?
                self.ProcessData(datachunk)
            # Data after the last newline, usually empty.
            self.datatemp = datas[-1]
        else:  # partial data.
            self.datatemp += data


# Start workers
g_workerlist, g_inqueue = createworkerpool(worker, CFG['NWORKERS'])

# Set up the Twisted application
application = service.Application("django-xmppface s2s server")

# outqueue.
outFactory = protocol.Factory()
outFactory.protocol = OutqueueHandler
outService = strports.service('unix:%s:mode=770' %
  CFG['SOCKET_ADDRESS'], outFactory)
outService.setServiceParent(application)

router = component.Router()

serverService = server.ServerService(router, domain=CFG['DOMAIN'],
  secret=CFG['SECRET'])
serverService.logTraffic = CFG['LOG_TRAFFIC']

s2sFactory = server.XMPPS2SServerFactory(serverService)
s2sFactory.logTraffic = CFG['LOG_TRAFFIC']
s2sService = strports.service(CFG['S2S_PORT'], s2sFactory)
s2sService.setServiceParent(application)

internalRouterComponent = component.InternalComponent(router,
  CFG['DOMAIN'])
internalRouterComponent.logTraffic = CFG['LOG_TRAFFIC']
internalRouterComponent.setServiceParent(application)

presenceHandler = PresenceHandler()
presenceHandler.setHandlerParent(internalRouterComponent)

vcardHandler = VCardHandler()
vcardHandler.setHandlerParent(internalRouterComponent)

msgHandler = MessageHandler()
msgHandler.setHandlerParent(internalRouterComponent)

# Note: possible problem:
# http://stackoverflow.com/questions/1470850/
