#!/bin/sh
# Start the XMPP server wia twistd.
exec ENV/bin/python /usr/bin/twistd -y xmppface/xmppserver.tac -n \
  --pidfile var/xmppserver.pid
