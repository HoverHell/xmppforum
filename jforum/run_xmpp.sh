#!/bin/sh
exec ../ENV/bin/python /usr/bin/twistd -y jaboardxmpp.tac -n --pidfile \
  jaboardxmpp.pid
