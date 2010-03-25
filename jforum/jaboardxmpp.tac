"""
An XMPP echo server as a standalone server via s2s.

This echo server accepts and initiates server-to-server connections using
dialback and listens on C{127.0.0.1} with the domain C{localhost}. It will
accept subscription requests for any potential entity at the domain and
send back messages sent to it.
"""

from twisted.application import service, strports
from twisted.words.xish import domish  # For creating messages to send.
from twisted.words.protocols.jabber.xmlstream import toResponse
from wokkel import component, server, xmppim
from sys import stdout, stderr

# Configuration parameters

S2S_PORT = 'tcp:5279:interface=0.0.0.0'
SECRET = 'secret'
DOMAIN = 'bot.hell.orts.ru'
LOG_TRAFFIC = True
NWORKERS = 2

# Global address of socket interface for sending XMPP messages.
# Only AF_UNIX socket for now. Non-crossplatform but somewhat easy to fix.
SOCKET_ADDRESS = 'xmppoutqueue'


## External: xmppworkerpool
from multiprocessing import Process, Queue, active_children, current_process
from thread import start_new_thread
import traceback  # Debug on exceptions.
import signal  # Sigint handler.
import time  # Old processes killing timeout.

import socket  # outqueue.
import os  # For screwing with the socket file
import simplejson  # Decoding of IPC data.

import xmppworker


def returner():
    # Socket init happens here.
    try:
        # It's /probably/ unused.
        # ! Should check that, actually.
        os.remove(SOCKET_ADDRESS)
    except:
        pass  # We don't care.
    outqueue = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    outqueue.bind(SOCKET_ADDRESS)
    try:
        # Should prefer more secure mode when possible.
        os.chmod(fname, 0770)
    except:
        server.log.err(" W: Could not chmod socket file.\n")
    while True:
        indata = outqueue.recv(65535)  # ! We have a limit here
        server.log.err(" D: Outqueue data: %r.\n" % indata)
        # We expect it to be simplejson data, possibly multiple lines (since
        # simplejson here shouldn't contain newlines itself).
        for dataline in indata.split("\n"):
            try:
                x = simplejson.loads(dataline)
                server.log.err(" D: Got JSON of length %d" % len(dataline))
                # Create and send a response.
                response = domish.Element((None, 'message'))
                response['type'] = 'chat'
                # Values are supposed to be always present here:
                response['to'] = x['dst']
                response['from'] = x['src']
                if 'content' in x:
                    # We're provided with raw content already.
                    response.addRawXml(x['content'])
                else:  # Construct it then.
                    # ! this all might be not really necessary.
                    if 'subject' in x:
                        response.addElement('subject', content=x['subject'])
                    # Body content is xml-escaped - likely, more than needed.
                    response.addElement('body', content=x['body'])
                    if 'html' in x:
                        htmlbody = domish.Element(
                          ('http://www.w3.org/1999/xhtml', 'body'))
                        htmlbody.addRawXml(x['html'])
                        htmlpart = domish.Element(
                          ('http://jabber.org/protocol/xhtml-im', 'html'))
                        htmlpart.addChild(htmlbody)
                        response.addChild(htmlpart)
                msgHandler.send(response)
            except ValueError:
                server.log.err(" E: Failed processing: %r" % dataline)


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
            server.log.err(" W: finishworkersgracefully: killing " \
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
        server.log.err("E: Reload FAILED.")
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

        # ? Should dump it to/from database also, maybe?
        """
        self.statustext = u"Greetings"
        self.subsribedto = {}

    def subscribedReceived(self, presence):
        server.log.err(" D: A: subscribedReceived.")
        """
        Subscription approval confirmation was received.

        This is just a confirmation. Don't respond.
        """
        self.subscribedto[presence.sender] = True
        pass

    def unsubscribedReceived(self, presence):
        server.log.err(" D: A: unsubscribedReceived.")
        """
        Unsubscription confirmation was received.

        This is just a confirmation. Don't respond.
        """
        if presence.sender in self.subscribedto:
            del(self.subscribedto[presence.sender])
        pass

    def subscribeReceived(self, presence):
        server.log.err(" D: A: subscribeReceived.")
        """
        Subscription request was received.

        Always grant permission to see our presence.
        """
        # ? Should also ask for subscription in turn?
        self.subscribed(recipient=presence.sender,
                        sender=presence.recipient)
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)

    def unsubscribeReceived(self, presence):
        server.log.err(" D: A: unsubscribeReceived.")
        """
        Unsubscription request was received.

        Always confirm unsubscription requests.
        """
        self.unsubscribed(recipient=presence.sender,
                          sender=presence.recipient)

    def probeReceived(self, presence):
        server.log.err(" D: A: probeReceived.")
        """
        A presence probe was received.

        Always send available presence to whoever is asking.
        """
        self.available(recipient=presence.sender,
                       status=self.statustext,
                       sender=presence.recipient)


class MessageHandler(xmppim.MessageProtocol):
    """
    Message echoing XMPP subprotocol handler.
    """

    def onMessage(self, message):
        server.log.err(" D: A: onMessage.")
        """
        Called when a message stanza was received.
        """

        # Ignore error messages
        if message.getAttribute('type') == 'error':
            server.log.err(" D: W: error-type message.")
            return

        ## Note: possible types are 'chat' and no type (ergo, plain non-chat
        ## message).
        ## But are there other types besides those and 'error'?
        type = message.getAttribute('type')
        if not (type == 'chat'):
            # For now - log them.
            server.log.err(" D: message of type %r." % type)
        try:
            src = message.getAttribute('from')
            dst = message.getAttribute('to')
            cmd = message.body
            id = message.getAttribute('id')
            name = message.name
            # Might it be not 'message'?
            server.log.err(" D: message name: %r." % message.name)

            inqueue.put_nowait({'src': src, 'dst': dst, 'cmd': cmd, \
              'ext': {'id': id, 'name': name, 'type': type}})
        except:
            # Something went pretty.wrong.
            server.log.err(" E: onMessage: exception.")
            traceback.print_exc()


# * Use twistd's --pidfile to write PID.

# Starting workers...
start_new_thread(returner, ())
workerlist, inqueue = createworkerpool(xmppworker.worker, NWORKERS)


# Set up the Twisted application
application = service.Application("Jaboard Server")

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

msgHandler = MessageHandler()
msgHandler.setHandlerParent(echoComponent)
