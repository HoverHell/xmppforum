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
