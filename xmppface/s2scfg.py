""" XMPP S2S server configuration provider.
Tries to grab the configuration overrides from an importable 'settings'
module. """

CFG_DEF = {
  'DOMAIN': 'bot.example.org',
  'LOG_TRAFFIC': True,
  'NWORKERS': 2,
  'S2S_PORT': 'tcp:5269:interface=0.0.0.0',
  'SECRET': 'secret',
  'SOCKET_ADDRESS': 'xmppoutqueue',
}

def cfg_override(settings_module, cfg=CFG_DEF):
    """ Grab whatever was overriden in settings. """
    for key, val in cfg.iteritems():
        cfg[key] = getattr(settings_module, key, val)
    return cfg
