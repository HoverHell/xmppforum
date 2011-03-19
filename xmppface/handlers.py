""" Default set of various handlers.  Currently - xmpp_post handler."""

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import simplejson

from .xmppface import processcmd

import logging
_log = logging.getLogger(__name__)
import traceback


## ! TODO: hand over cookie using HTTP headers?  Or use HTTP basic auth?
## ? XXX: Move this to xmppface, maybe?
def xmpp_post(request):
    """ Handles XMPP stuff handed to the django over HTTP POST.  """
    try:
        datas = request.raw_post_data  # not encoded in there.
        if not datas:  # empty?..
            return HttpResponse('---')
        data = simplejson.loads(datas)
        
        ## Check simple-security-cookie:
        rcookie = data.pop('postcookie', None)
        if rcookie != settings.POSTCOOKIE:
            raise PermissionDenied('No no no!')

        processcmd(data)
    except Exception:
        _log.exception("Error on processing POSTed XMPP data.")
    return HttpResponse('.')
