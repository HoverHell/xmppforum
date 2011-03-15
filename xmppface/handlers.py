""" Default set of various handlers.  """

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import simplejson

from .xmppface import processcmd


## ! TODO: hand over cookie using HTTP headers?  Or use HTTP basic auth?


def xmpp_post(request):
    """ Handles XMPP stuff handed to the django over HTTP POST.  """
    datas = request.raw_post_data  # not encoded in there.
    data = simplejson.loads(datas)
    
    ## Check simple-security-cookie:
    rcookie = data.pop('postcookie', None)
    if rcookie != settings.POSTCOOKIE:
        raise PermissionDenied('No no no!')

    processcmd(data)
    return HttpResponse('.')


## ! TODO: Implement (sample) handle404 / handlecmd404 / handle403 / handle500
##  here and use them from processcmd?
##  !! Perhaps not here - to avoid circular dependencies.  Or move xmpp_post
##   somewhere else, instead.  More likely they should be in views after
##   all.
