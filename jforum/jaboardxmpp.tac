"""
A jaboard XMPP face server as a standalone server via s2s.
"""

from twisted.application import service, strports
from twisted.internet import protocol
from twisted.words.xish import domish  # For creating messages to send.
from wokkel import component, server, xmppim
from sys import stdout, stderr


# Default configuration parameters. Overriden by ones in settings.
S2S_PORT = 'tcp:5269:interface=0.0.0.0'
SECRET = 'secret'
DOMAIN = 'bot.example.org'
LOG_TRAFFIC = True
NWORKERS = 2
SOCKET_ADDRESS = 'xmppoutqueue'

from settings import *  # override whatever...

## External: xmppworkerpool

# Try to use django to get best available json library
try:
    from django.utils import simplejson # Decoding of IPC data.
except ImportError:
    # Huh? No Django? Well, okay. We're abstract enough.
    import simplejson

import traceback  # Debug on exceptions.

from multiprocessing import Process, Queue, active_children, current_process
from thread import start_new_thread
import signal  # Sigint handler.
import time  # Old processes killing timeout.

import xmppworker


def createworkerpool(targetfunc, nworkers):
    """
    Creates nworkers of workers, running func.

    func should take (inqueue, ) as arguments.

    Returns tuple (workerlist, inqueue)
    """
    inqueue = Queue()
    workerlist = []
    for i in xrange(nworkers):
        w1 = Process(target=targetfunc, args=(inqueue, ))
        w1.start()
        workerlist.append(w1)
    return (workerlist, inqueue)

# ! terminate() was not added here because it seems not very necessary.


def finishworkersgracefully(workerlist, inqueue):
    for i in xrange(len(workerlist) + 1):  # +1 is doubtul
        inqueue.put("QUIT")
    # Does that do something?
    inqueue.close()
    inqueue.join_thread()
    time.sleep(20)  # If they still live - we've got some serious problem.
    for workprc in workerlist:
        if workprc.is_alive():
            server.log.err(" ------- W: finishworkersgracefully: killing " \
             "still-alive worker %r." % workprc)
            workprc.terminate()
        del(workprc)


def sighuphandler(signum, frame):
    # reload!
    # Shouldn't be executed in child processes, btw.
    global inqueue, workerlist, NWORKERS
    try:
        reload(xmppworker)
    except:
        server.log.err(" -------------- E: Reload FAILED.")
        traceback.print_exc()
        return
    inqueueold, workerlistold = inqueue, workerlist
    workerlist, inqueue = createworkerpool(xmppworker.worker, NWORKERS)
    while not inqueueold.empty():
        try:
            r = inqueueold.get_nowait()
            inqueue.put_nowait(r)
        except Empty:
            break
    start_new_thread(finishworkersgracefully, (workerlistold, inqueueold))
signal.signal(signal.SIGHUP, sighuphandler)

if __name__ == "__main__":  # main modue - handle signals.
    server.log.err(" XXX: main. ")
    def sigtermhandler(signum, frame):
        server.log.err(" XXX: sigtermed. ")
        global inqueue, workerlist, NWORKERS
        finishworkersgracefully(workerlist, inqueue)
    signal.signal(signal.SIGTERM, sigtermhandler)


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
        for child in element.elements():  # usually only one.
            if child.name == 'photo':
                if child.children:
                    self.photo = child.children[0]
                else:
                    self.photo = ""


# Protocol handlers
class PresenceHandler(xmppim.PresenceProtocol):
    """
    Presence accepting XMPP subprotocol handler.

    This handler blindly accepts incoming presence subscription requests,
    confirms unsubscription requests and responds to presence probes.

    Note that this handler does not remember any contacts, so it will not
    send presence when starting.
    """
    
    
    def __init__(self):
        """
        Some data to store.
        """
        self.statustext = u"Greetings"
        self.subscribedto = {}
        # small hack (attempt):
        self.presenceTypeParserMap['available'] = AvailabilityPresenceX
        # ! Ask django-xmppface to ask self to send presences.

    def subscribedReceived(self, presence):
        """
        Subscription approval confirmation was received.

        Saves that information.
        """
        server.log.err(" ------- D: A: subscribedReceived.")
        inqueue.put_nowait({'auth': 'subscribed',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})


    def unsubscribedReceived(self, presence):
        """
        Unsubscription confirmation was received.

        Save (update) that information.
        """
        server.log.err(" ------- D: A: unsubscribedReceived.")
        inqueue.put_nowait({'auth': 'unsubscribed',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})


    def subscribeReceived(self, presence):
        """
        Subscription request was received.

        Always grant permission to see our presence.
        """
        server.log.err(" ------- D: A: subscribeReceived.")
        self.subscribed(recipient=presence.sender,
                        sender=presence.recipient)
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)
        # Ask for subscription in turn.
        # ? Need some extracheckings for that?
        server.log.err(" ------- D: A: Requesting mutual subscription... ")
        self.subscribe(recipient=presence.sender,
                        sender=presence.recipient)
        inqueue.put_nowait({'auth': 'subscribe',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})


    def unsubscribeReceived(self, presence):
        """
        Unsubscription request was received.

        Always confirm unsubscription requests.
        """
        server.log.err(" ------- D: A: unsubscribeReceived.")
        self.unsubscribed(recipient=presence.sender,
                          sender=presence.recipient)
        inqueue.put_nowait({'auth': 'unsubscribe',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def availableReceived(self, presence):
        """
        Available presence was received.
        """
        server.log.err(" ------- D: A: availableReceived. show: %r" % (
          presence.show,))
        show = presence.show or "online"
        inqueue.put_nowait({'stat': show,
           'photo': getattr(presence, 'photo', None),
           'src': presence.sender.full(), 'dst': presence.recipient.full()})


    def unavailableReceived(self, presence):
        """
        Unavailable presence was received.
        """
        server.log.err(" ------- D: A: unavailableReceived.")
        inqueue.put_nowait({'stat': 'unavail',
           'src': presence.sender.full(), 'dst': presence.recipient.full()})

    def probeReceived(self, presence):
        """
        A presence probe was received.

        Always send available presence to whoever is asking.
        """
        server.log.err(" ------- D: A: probeReceived.")
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)


class MessageHandler(xmppim.MessageProtocol):
    """
    Message echoing XMPP subprotocol handler.
    """

    def onMessage(self, message):
        """
        Called when a message stanza was received.
        """
        server.log.err(" ------- D: A: onMessage.")

        # Ignore error messages
        if message.getAttribute('type') == 'error':
            server.log.err(" -------------- D: W: error-type message.")
            return

        ## Note: possible types are 'chat' and no type (ergo, plain non-chat
        ## message).
        # ? But are there other types besides those and 'error'?
        try:
            type = message.getAttribute('type')
            if type == 'headline':
                # ? Something interesting in those?
                # (see note2.txt for example)
                return  # ...or just skip them.
            if not (type == 'chat'):
                # For now - log them.
                server.log.err(" ------- !! D: message of type %r." % type)
            name = message.name
            # Might it be not 'message'?
            if not (name == 'message'):
                server.log.err(" ------- !! D: message name: %r." % message.name)

            # Dump all the interesting parts of data to the processing.
            inqueue.put_nowait(
              {'src': message.getAttribute('from'),
               'dst': message.getAttribute('to'),
               'body': message.body.children[0],
               'id': message.getAttribute('id'),
               'type': message.getAttribute('type'),
              })
        except:
            # Something went pretty.wrong.
            server.log.err(" -------------- E: onMessage: exception.")
            traceback.print_exc()


try:
    from twisted.words.protocols.xmlstream import XMPPHandler
except ImportError:
    from wokkel.subprotocols import XMPPHandler
VCARD_RESPONSE = "/iq[@type='result']/vCard[@xmlns='vcard-temp']"
class VCardHandler(XMPPHandler):
    """ """
    
    def connectionInitialized(self):
        """
        Called when the XML stream has been initialized.

        This sets up an observer for incoming stuff.
        """
        self.xmlstream.addObserver(VCARD_RESPONSE, self.onVcard)

    def _jparse(el):
        """ Parses the provided XML element, returning recursed dict with its
        data (ignoring *some* text nodes). """
        if not el.firstChildElement():  # nowhere to recurse to.
            return unicode(el)  # perhaps there's some string, then.
        outd = {}
        for child in el.elements():  # * ignoring other text nodes, actually
            # * ...and overwriting same-name siblings, apparently.
            outd[child.name] = jparser(child)
        return outd

    def onVcard(self, iq):
        server.log.err("onVcard. iq: %r" % iq)
        server.log.err(" ... %r" % iq.children)
        vc = iq.firstChildElement()
        if vc:
            inqueue.put_nowait(
              {'src': message.getAttribute('from'),
               'dst': message.getAttribute('to'),
               'vcard': self._jparse(vc)})


class OutqueueHandler(protocol.Protocol):
    def connectionMade(self):
        stderr.write(" D: OutqueueHandler: connection received.\n")
        
    datatemp = ""  # for holding partially reveived data
    dataend = "\n"  # End character for splitting datastream.
    
    def ProcessData(self, dataline):
        """
         Called from dataReceived for an actual combined data ready for
         processing (which is determined by newlines in the stream,
         actually)..
        """
        try:
            x = simplejson.loads(dataline)
            server.log.err(" ------- D: Got JSON line of length %d:" % len(dataline))
            server.log.err(" --    %r        --\n  " % x)
            if 'class' in x:
                server.log.err("1")
                response = domish.Element((None, x['class']))
                # Values are supposed to be always present here:
                server.log.err("2")
                response['to'] = x['dst']
                response['from'] = x['src']
                server.log.err("3")
                for extranode in ('type', 'xml:lang'):
                    if extranode in x:
                        response[extranode] = x[extranode]
                server.log.err("4")
                if 'content' in x:
                    # We're provided with raw content already.
                    # It is expected to be valid XML already.
                    # (if not - remote server will probably drop s2s connection)
                    response.addRawXml(x['content'])
                server.log.err("5")
                if x['class'] == 'message':
                    # Create and send a response.
                    response['type'] = response.getAttribute('type') or 'chat'
                    if not 'content' in x:
                        # This should be done in XmppResponse. Removing it from here.
                        pass
                # Everything else should be in place already for most types.
                server.log.err("6")
                server.log.err(" r: %r" % response)
                server.log.err(" rr: %r" % response.toXml())
                server.log.err("7")
                msgHandler.send(response)
            else:  # not 'class'
                pass  # Nothing else implemented yet.
        except ValueError:
            server.log.err(" -------------- E: Failed processing:" \
             " %r" % dataline)

    def dataReceived(self, data):
        # Process received data for messages to send.
        server.log.err(u" ------- D: Received data (%r) of len %d with %d "
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

# * Use twistd's --pidfile to write PID.


# Starting workers...
workerlist, inqueue = createworkerpool(xmppworker.worker, NWORKERS)

# Set up the Twisted application
application = service.Application("Jaboard Server")

# outqueue.
outFactory = protocol.Factory()
outFactory.protocol = OutqueueHandler
outService = strports.service('unix:%s:mode=770'%SOCKET_ADDRESS, outFactory)
outService.setServiceParent(application)

router = component.Router()

serverService = server.ServerService(router, domain=DOMAIN, secret=SECRET)
serverService.logTraffic = LOG_TRAFFIC

s2sFactory = server.XMPPS2SServerFactory(serverService)
s2sFactory.logTraffic = LOG_TRAFFIC
s2sService = strports.service(S2S_PORT, s2sFactory)
s2sService.setServiceParent(application)

echoComponent = component.InternalComponent(router, DOMAIN)
echoComponent.logTraffic = LOG_TRAFFIC
echoComponent.setServiceParent(application)

presenceHandler = PresenceHandler()
presenceHandler.setHandlerParent(echoComponent)

vcardHandler = VCardHandler()
vcardHandler.setHandlerParent(echoComponent)

msgHandler = MessageHandler()
msgHandler.setHandlerParent(echoComponent)

