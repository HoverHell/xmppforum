""" Default URLs for XMPP-related handling.  Include to root.  """

from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'^_xmpp/postdata', 'xmppface.handlers.xmpp_post', {}, 'xmpp_post'),
)
