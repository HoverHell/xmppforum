"""
This module is an unfinished (yet) attempt to add XMPP/IM/cmd support to
django in the same way that it implements HTTP/HTML.

This is the face-part, which tries to return some response for entered command.
"""

import django
from django.utils.translation import ugettext as _

# cmdresolver / urlresolver. May be a hack..
from django.core.urlresolvers import RegexURLResolver
# Now that's surely a hack, eh?
from cmds import cmdpatterns

from xmppbase import *

# Couple of things here should probably be in a class.
# Place something instead of "", maybe?
cmdresolver = RegexURLResolver("", cmdpatterns)

# Debug...
import sys
import traceback

# Fixin'
import re
lastnewlinere = re.compile("\n+$")

def processcmd(src, dst, cmd, ext=None):
    """
    Gets a source jid and command text and returns XmppResponse.
    """
    sys.stderr.write("\nD: src: %r; cmd: %r\n" % (src, cmd))
    # src may contain a resource.
    srcbarejid = src.split("/")[0]
    request = XmppRequest(srcbarejid)
    cmd = str(cmd)  # Make sure it's a string.
    # ! Also, it might be multiline.
    sys.stderr.write("\nD: cmdstr: cmd: %r\n" % (cmd))
    try:
        # ! State-changing might be required, e.g. for multi-part commands.
        #sys.stderr.write("\nD: resolving...")
        callback, callback_args, callback_kwargs = cmdresolver.resolve(cmd)
        # Populate request.POST from cmd? Or modify views instead?

        sys.stderr.write("\nD: callback: %r; args: %r; kwargs: %r\n" % \
          (callback, callback_args, callback_kwargs))

        # ...Also, middleware? it's not likely to support XmppResponse though.

        try:
            response = callback(request, *callback_args, **callback_kwargs)

            # ! We do expect an XmppResponse here.
            if not isinstance(response, XmppResponse):
                sys.stderr.write("\n E: callback (%r (%r, %r))" % \
                  (callback, callback_args, callback_kwargs) + \
                  " returned non-XmppResponse object %r.\n" % response)
                raise TypeError("Response is not response!")

            # May also add registration offer to anonymous users.
        except django.http.Http404, e:
            # Using Http404 here not very right, eh?
            # But is certainly more simple.

            # ? Not sure what would it take to make 404-message view-specific.
            # (ex.: "Thread not found")
            response = XmppResponse(_("Not found."))

        except Exception, e:
            response = XmppResponse(_("Sorry, something went wrong!\n" \
              "Don't worry, admins weren't notified!"))
            sys.stderr.write("\n E: Exception when calling callback:")
            sys.stderr.write(traceback.format_exc())
        # Not final. Also, toResponse(), part 1.
    except django.http.Http404, e:
        # Http404 from resolver.
        response = XmppResponse(_("No such command. Try 'HELP', maybe?"))
    # Fix possible extraneous newlines.
    response['body'] = lastnewlinere.sub(u'', response['body'])
    # Return back with exactly the same full JIDs.
    response['src'] = dst
    response['dst'] = src
    response['subject'] = "Jaboard: XMPP"
    # ! May populate other values from a possible 'ext' here.
    return response

# Testing:
#processcmd("hell@hell.orts.ru", "bot@bot.hell.orts.ru", "#")
