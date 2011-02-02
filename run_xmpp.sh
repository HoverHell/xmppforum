#!/bin/sh
exec ENV/bin/python /usr/bin/twistd -y xmppface/jaboardxmpp.tac -n \
  --pidfile var/jaboardxmpp.pid
