"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the face-part, which tries to return some response for entered command.
"""

import django
from django.utils.translation import ugettext as _

"""
from django.shortcuts import render_to_response as render_to_response_orig
#from django.contrib.auth.models import User
# User class is modified in here.
from models import User 
"""

# cmdresolver / urlresolver. Likely to be a crude hack.
from django.core.urlresolvers import RegexURLResolver
# Now that's surely a hack, eh?
from cmds import cmdpatterns

from xmppbase import *

# Couple of things here should probably be in a class.
# Place something instead of "", maybe?
cmdresolver=RegexURLResolver("", cmdpatterns)

# Debug...
import sys
import traceback

        
def processcmd(src, dst, cmd, ext = None):
    """
    Gets a source jid and command text and returns XmppResponse.
    """
    sys.stderr.write("\nD: src: %r; cmd: %r\n" % (src, cmd))
    # src may contain a resource.
    srcbarejid = src.split("/")[0]
    request=XmppRequest(srcbarejid)
    cmd = str(cmd) # Make a string from it?
    sys.stderr.write("\nD: cmdstr: cmd: %r\n" % (cmd))
    try:
        # ! State-changing might be required, e.g. for multi-part commands.
        #sys.stderr.write("\nD: resolving...")
        callback, callback_args, callback_kwargs = cmdresolver.resolve(cmd)
        # Populate request.POST from cmd? Or modify views instead?
        
        sys.stderr.write("\nD: callback: %r; args: %r; kwargs: %r\n" % (callback,
          callback_args, callback_kwargs))
        
        # ...Also, middleware? it's not likely to support XmppResponse though.
        
        try:
            response = callback(request, *callback_args, **callback_kwargs)
            
            # ! We do expect an XmppResponse here.
            if not isinstance(response, XmppResponse):
                sys.stderr.write("\n E: callback (%r (%r, %r))" % (callback, callback_args,
                  callback_kwargs) + " returned non-XmppResponse "+
                  "object %r.\n" % response)
                raise TypeError("Response is not response!")
            
            # May also add registration offer to anonymous users.
            #return response
        except django.http.Http404, e:
            # Using Http404 here not very right, eh?
            # But is certainly more simple.
            
            # ? Not sure what would it take to make 404-message view-specific.
            # (ex.: "Thread not found")
            response = XmppResponse(_("Not found."))
            
        except Exception, e:
            # What should we do here?
            responsestr = _("Sorry, something went wrong!")
            response = XmppResponse(responsestr)
            # Debug
            sys.stderr.write("\n E: Exception when calling callback:")
            sys.stderr.write(traceback.format_exc())
        # Not final. Also, toResponse(), part 1.
    except django.http.Http404, e:
        # No such command, eh?
        response = XmppResponse(_("No such command. Try 'HELP', maybe?"))
    response.src = dst
    response.dst = src
    return response


      
# Testing:
#processcmd("hell@hell.orts.ru", "#")
