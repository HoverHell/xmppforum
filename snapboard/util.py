""" Helper stuff specific to this project (even if reusable).  """

from django.core.exceptions import PermissionDenied

## Helper wrapper, used instead of
## django.contrib.admin.views.decorators.staff_member_required for using it
## with XMPP and RPC requests.
def staff_required(view_func):
    """ Decorator for views that checks that the user is logged in and is a
    staff member, returning PermissionDenied otherwise.  """
    def _checklogin(request, *args, **kwargs):
        """ Internal wrapper for staff_required.  """
        if request.user.is_active and request.user.is_staff:
            # The user is valid. Continue to the admin page.
            return view_func(request, *args, **kwargs)
        # Only users with staves are allowed to do that!
        raise PermissionDenied, "You should be an admin to do that."
    from functools import wraps
    return wraps(view_func)(_checklogin)


## Diff stuff.
import re
import difflib
def _diff_processtext(text):
    """ Prepares the supplied post text to be diff'ed.  """
    from snapboard.templatetags.extras import render_filter
    texth = render_filter(text)  # -> html
    textl = re.findall(r'<[^>]*?>|[^<]+', texth)  # -> tags&text
    out = []
    for item in textl: # -> tags & words.
        if item.startswith("<"):
            out.append(item)
        else:
            #out += item.split()  # Extra spaces?
            out += re.findall(r'[ ]+|[^ ]+', item)
    return out


def _diff_texts(text1, text2):
    """ Returns a list with differences between two processed HTML texts,
    ready for rendering.  """
    prevt = None  # type of the previous diff item.
    datas = ""  # collected continuous data.
    listv = []  # resulting list.
    for item in difflib.ndiff(text1, text2):
        # Gets HTML tags as plain non-changed from the newer version.
        if item.startswith('+ <'):
            type, data = "  ", item[2:]
        elif item.startswith('- <'):
            type = None  # ignore removed tags.
        else:
            type, data = item[:2], item[2:]
        if type is not None:
            if prevt == type:
                datas += data  # add them all later.
            else:  # different type.
                listv.append((prevt, datas))
                prevt, datas = type, data
    # end.
    listv.append((prevt, datas))  # append remains.
    return listv


def _diff_posts(post1, post2):
    """ Returns a list with differences between two posts (pre-processing
    the text or using it cached in the post.  """
    def _get_text(post):
        text = getattr(post, 'text_diffprocessed', None)
        if text is None:
            text = _processtext(post.text)
            post.text_diffprocessed = text  # might be used once more.
        return text
    return _diff_texts(_get_text(prev_post), _get_text(post))
