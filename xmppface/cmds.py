""" A sample / utility command patterns that can be plugged in if needed.  """

from django.conf.urls.defaults import patterns
from .views import (xmpp_register_cmd, xmpp_unregister_cmd,
  xmpp_web_login_cmd, xmpp_web_changepw)

cmdpatterns = patterns('',
    (r'^(?i)reg(?:ister)?( +(?P<nickname>.+?)( +-p (?P<password>.+))?)?$',
      xmpp_register_cmd, {}, 'xmpp_register_cmd'),
    (r'^(?i)unregister!$', xmpp_unregister_cmd, {}, 'xmpp_unregister_cmd'),
    (r'^(?i)log(?:in)?$', xmpp_web_login_cmd, {}, 'xmpp_login_cmd'),
    (r'^(?i)password( (?P<password>.+))?$',
      xmpp_web_changepw, {}, 'xmpp_changepw'),
)
