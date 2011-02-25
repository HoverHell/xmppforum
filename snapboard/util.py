""" Helper stuff specific to this project (even if reusable).  """

from django.core.exceptions import PermissionDenied
from django.conf import settings


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


## Other RPC stuff.
def r_getreturn(request, rpc=False, rpcdata={}, successtext=None,
  nextr=None, postid=None):
    """ Common function for RPCable views to easily return some appropriate
    data (rpcdata or next-redirect).  """
    if rpc:  # explicit request to return RPC-usable data
        # do conversion in rpc().
        return rpcdata
    else:
        if successtext is None and 'msg' in rpcdata:
            successtext = rpcdata['msg']
        if request.is_xmpp():  # simplify it here.
            return XmppResponse(successtext)
        # ! TODO: Add a django-mesasge if HTTP?
        nextr = nextr or request.GET.get('next')
        if nextr:  # know where should return to.
            return HttpResponseRedirect(nextr)
        else:  # explicitly return 
            if postid:  # we have a post to return to.
                # msg isn't going to be used, though.
                return success_or_reverse_redirect('snapboard_thread_post',
                  args=(postid,), req=request, msg=successtext)
            else:
                # Might supply some more data if we need to return somewhere
                # else?
                return HttpResponseServerError(
                  "RPC return: unknown return.")  # Nothing else to do here.


## Timedelta stuff.
# configurable/overridable:
TIMEDELTA_NAMES = getattr(settings, 'TIMEDELTA_NAMES',
  ('y', 'mo', 'w', 'd', 'h', 'm', 's'))
TIMEDELTA_MAXLEN = getattr(settings, 'TIMEDELTA_MAXLEN', 0)
TIMEDELTA_SIZES = (
  3600 * 24 * 365, 3600 * 24 * 30, 3600 * 24 * 7, 3600 * 24, 3600, 60, 1
)
TIMEDELTA_UNITS = zip(TIMEDELTA_NAMES, TIMEDELTA_SIZES)


from datetime import timedelta
def format_timedelta(delta, maxlen=TIMEDELTA_MAXLEN):
    """ Return a time delta (seconds or timedelta) as human-readable.  """
    if isinstance(delta, timedelta):
        seconds = abs(int((delta.days * 86400) + delta.seconds))
    else:
        seconds = abs(delta)

    a_res = []
    for unit, secs_per_unit in TIMEDELTA_UNITS:
        if not unit:
            continue
        value = seconds // secs_per_unit
        seconds %= secs_per_unit
        if value > 0:
            a_res.append(u"%d%s" % (value, unit))
            if maxlen and  len(a_res) >= maxlen:
                break
    return u' '.join(a_res)


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
        elif item.startswith('? '):
            # nothing to do with intra-line diff annotations.  They might be
            # inside HTML tags after all.
            type = None
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
            text = _diff_processtext(post.text)
            post.text_diffprocessed = text  # might be used once more.
        return text
    return _diff_texts(_get_text(post1), _get_text(post2))


## Paging stuff
def _find_depth(qs, startdepth=1, approxnum=20):
    """ Finds a target maximal depth that will result in minimal amount of
    objects which is still more than approxnum.  """
    # ! TODO: Cache.
    _get_try = lambda depth: qs.filter(depth__lte=depth).count()
    ## Step 1: find approximation level 1.
    res = 5  # starting point.
    last = "x"  # for checking if there's no deeper posts.
    cur = _get_try(res)
    while cur < approxnum and last != cur:
        last = cur
        res *= 2
        cur = _get_try(res)
    if last == cur:
        return res  # there's less than approxnum anyway.
    # Step 2: find approximation between last and cur (with binary search).
    lo, hi = res // 2, res  # current and previous attempts.
    while last != cur and lo < hi:
        res_p, res = res, (lo + hi) // 2
        last = cur
        cur = _get_try(res)
        if cur < approxnum:  # not enough, seek higher.
            lo = res
        else:  # too much, seek lower
            hi = res
    return res if cur > approxnum else res + 1
