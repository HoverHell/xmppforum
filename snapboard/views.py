import logging
import datetime
import time

from django import forms
from django.conf import settings
from django.contrib.auth import decorators
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.core.cache import cache

# For easy notification resource handling:
from notification import models as notification

#from django.contrib.auth.decorators import login_required
# XmppFace
import xmppface.xmppbase
from xmppface.xmppbase import (XmppRequest, XmppResponse, render_to_response,
 success_or_reverse_redirect, login_required, get_login_required_wrapper)
from xmppface.xmppstuff import send_notifications

# Avatar form in UserSettings
from avatar.models import Avatar, avatar_file_path
from avatar.forms import PrimaryAvatarForm, UploadAvatarForm
from avatar.views import _get_avatars, _notification_updated

from django.contrib.sites.models import Site

from snapboard.forms import *
from snapboard.models import *
from snapboard.models import AnonymousUser
from snapboard.rpc import *

_log = logging.getLogger('snapboard.views')


ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', 'Anonymous')
CAT_REMTHREADS_NAME = getattr(settings, 'CAT_REMTHREADS_NAME',
  'Removed Threads')

if ANONYMOUS_NAME:
    ANONYMOUS_USER = User.objects.get(username=ANONYMOUS_NAME)
    def anonymous_login_required(function=None):
        """ Decorator to replace auth's AnonymousUser with an actual usable
        user for particular views.  Sets user.really_anonymous if replaced. 
        Configurable by ANONYMOUS_NAME in the settings.  """
        def anon_decorate(request, *args, **kwargs):
            if request.user.is_authenticated():
                return function(request, *args, **kwargs)
            else:  # Use Anonymous! Just for this request, of course.
                request.user = ANONYMOUS_USER
                request.user.really_anonymous = True
                return function(request, *args, **kwargs)
        return anon_decorate
else:
    def anonymous_login_required(function=None):
        return login_required(function)

        
def snapboard_default_context(request):
    """ Provides some default information for all templates.

    This should be added to the settings variable
    TEMPLATE_CONTEXT_PROCESSORS """
    # ? XXX: Add site.name here for use instead of 'XMPP Forum'?
    return {
      'SNAP_MEDIA_PREFIX': SNAP_MEDIA_PREFIX,
      'SNAP_POST_FILTER': SNAP_POST_FILTER,
      'LOGIN_URL': settings.LOGIN_URL,
      'LOGOUT_URL': settings.LOGOUT_URL,
      }


def _get_that_post(request, post_id=None):
    """ Helper function for allowing post-related commands unto unspecified
    "last notified" post.  Raises Http404 if cannot."""
    if post_id:
        post = get_object_or_404(Post, pk=post_id);
        return post
    # otherwise - find one!
    # TODO: include the user full jid into the search!..
    # (that will allow to make one-to-one conversations basically
    # seamlessly.
    now = time.time()
    ndata = cache.get('nt_%s' % request.user.username)
    if ndata:
        postid, ntime = ndata  # Shouldn't fail, really.
        if now - ntime < 1:  # For avoiding sudden mistakes. RealtimeWorx.
            return XmppResponse("You sure? Which post? Please confirm.")
        try:
            post = Post.objects.get(pk=postid)
        except Post.DoesNotExist:
            raise Http404, "Dunno such. Must've vanished. Specify precise post."
    else:
        raise Http404, "Dunno any. Specify precise post."


def user_settings_context(request):
    return {'user_settings': request.user.get_user_settings()}


extra_processors = [user_settings_context]


## XMPP registration/autoregistration stuff.
# TODO: move it to xmppface.views;
# also, probably need a global get_login_required_wrapper(xmpp_unreg_view)
# setting.

def xmpp_register_cmd(request, nickname=None, password=None):
    """ Provides all necessary registration-related functionality for XMPP.
    XMPP-only view.  """
    if nickname is None:  # Allow registration w/o specifying nickname.
        nickname = request.srcjid
    # We're going to register one anyway.
    ruser, created = User.objects.get_or_create(username=nickname)
    rusersettings, c = UserSettings.objects.get_or_create(user=ruser)
    if created:  # Okay, registered one.
        rusersettings.jid = request.srcjid
        if password is not None:
            ruser.set_password(password)
        ruser.save()
        rusersettings.save()
        return XmppResponse(_("Registration successful."))
    else:
        # Note: check_password can be True if passord is None
        if (password is not None) and ruser.check_password(password):
            if request.user.is_authenticated():
                # ? What to do here, really?
                return XmppResponse(_("You are already registered"))
            else:  # 'authenticate into' an existing webuser.
                rusersettings.jid = request.srcjid  # replace its JID
                # ! XXX: jid might be not unique!
                rusersettings.save()
                return XmppResponse(_("JID setting updated successfully."))
        else:
            raise PermissionError, "Authentication to an existing user failed."
    # Optional: change state to 'password input' if no password
    # !! Possible problem if password (or, esp., both) contain spaces.


def xmpp_autoregister_user(request, function, *args, **kwargs):
    """ If XMPP user needs to be registered - try to register, and tell
    either way.  """
    jidname = request.src.split('@')[0]
    from django.contrib.auth.models import User
    if User.objects.filter(username__iexact=jidname).exists():
        return XmppResponse("You have to register to do this."
          "Additionally, username '%r' is unavailable so I could not "
          "autoregister you" % jidname)
    else:  # no such user - just autoregister him!
        # Use that view to actually register:
        regresp = xmpp_register_cmd(request, jidname)
        # ? do the initial command, too? Perhaps not.
        return XmppResponse("You were just registered as '%s'. Please "
          "re-send the command to actually do it." % jidname)


login_required = get_login_required_wrapper(xmpp_autoregister_user)


## RPC/similar stuff:
# Okay, how this bicycle works:
# The idea is to make the same stuff process
# r) JavaScript/AJAX/RPC requests.
#   Should return some JSON or HTTP error.
# w) non-js web requests.
#   Usually return back (to the original post, for example).
#   ? Could use message-sets or write to the same place as RPC, maybe. But
#    not very important.
# x) XMPP requests.
#   Return some success (or error) message.
# .
# * Right now legacy javascript-only suff is used as well.


def rpc(request):
    """ Delegates simple rpc requests.  """
    if not request.POST:
        return HttpResponseServerError("RPC data is absent")
    
    if not request.user.is_authenticated():
        return HttpResponseServerError("RPC request by unauthenticated user")

    response_dict = {}

    try:
        action = request.POST['action'].lower()
        rpc_func = RPC_ACTION_MAP[action]
    except KeyError:
        raise HttpResponseServerError("RPC: Unknown RPC function")

    try:
        oid = int(request.POST['oid'])
    except KeyError:
        return HttpResponseServerError("RPC handler: KeyError, missing oid.")
    
    #if action == 'quote':
    #    try:
    #        return HttpResponse(simplejson.dumps(rpc_func(request, oid=int(request.POST['oid']))))
    #    except (KeyError, ValueError):
    #        return HttpResponseServerError("RPC: Failed to find/process requested post.")

    if action in RPC_AACTIONS:  # Just do it.
        # Note: django's exception handling in here.
        # Dict is expected for rpc=True call.
        response_dict.update(rpc_func(request, oid, rpc=True))
    else:  # Otherwise...
        try:
            # oclass_str will be used as a keyword in a function call, so it must
            # be a string, not a unicode object (changed since Django went
            # unicode). Thanks to Peter Sheats for catching this.
            oclass_str = str(request.POST['oclass'].lower())
            oclass = RPC_OBJECT_MAP[oclass_str]
        except KeyError:
            return HttpResponseServerError("RPC: Unknown requested object type.")

        try:  # process...
            forum_object = oclass.objects.get(pk=oid)
        except oclass.DoesNotExist:
            return HttpResponseServerError("RPC handler: no such object.")
        # Note: django's exception handling in here.
        response_dict.update(rpc_func(request, **{oclass_str:forum_object}))
    # pack the (whichever) result.
    return HttpResponse(simplejson.dumps(response_dict),
     mimetype='application/javascript')


def r_getreturn(request, rpc=False, next=None, rpcdata={}, successtext=None, postid=None):
    """ Common function for RPCable views to easily return some appropriate
    data (rpcdata or next-redirect).  """
    if rpc:  # explicit request to return RPC-usable data
        # do conversion in rpc().
        return rpcdata
    else:
        # ! XXX: Untested.
        if successtext is None and 'msg' in rpcdata:
            successtext = rpcdata['msg']
        if request.is_xmpp():  # simplify it here.
            return XmppResponse(successtext)
        # ! TODO: Add a django-mesasge if HTTP?
        next = next or request.GET.get('next')
        if next:  # know where should return to.
            return HttpResponseRedirect(next)
        else:  # explicitly return 
            if postid:  # we have a post to return to.
                # msg isn't going to be used, though.
                return success_or_reverse_redirect('snapboard_locate_post',
                  args=(postid,), req=request, msg=successtext)
            else:
                # Might supply some more data if we need to return somewhere
                # else?
                return HttpResponseServerError(
                  "RPC return: unknown return.")  # Nothing else to do here.


@login_required
def r_watch_post(request, post_id=None, next=None, resource=None, rpc=False):
    post = _get_that_post(request, post_id)
    # ^ 'auto' fetching should only be done from XMPP.
    thr = post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError, "You are not allowed to do that"
    try:
        # ! FIXME: This doesn't look very good.
        # ? Check if user's already subscribed to that branch? (post__in get_ancestors)
        # (if not - can use get_or_create here)
        wl = WatchList.objects.get(user=request.user, post=post)
        # it exists, stop watching it
        wl.delete()
        return r_getreturn(request, rpc, next, {'link':_('watch'),
          'msg':_('This thread has been removed from your favorites.')},
          "Watch removed.", postid=post.id)
    except WatchList.DoesNotExist:
        # create it
        wl = WatchList(user=request.user, post=post, xmppresource=resource)
        wl.save()
        return r_getreturn(request, rpc, next, {'link':_('dont watch'),
          'msg':_('This thread has been added to your favorites.')},
          "Watch added.", postid=post.id)

@login_required
def r_abusereport(request, post_id=None, next=None, resource=None, rpc=False):
    """ Report some inappropriate post for the admins to consider censoring. 
    """
    thr = post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError, "You are not allowed to do that"
    abuse = AbuseReport.objects.get_or_create(
      submitter = request.user,
      post = kwargs['post'],
      )
    return r_getreturn(request, rpc, next, {
       'link': '',
       'msg': _('The moderators have been notified of possible abuse')},
      "Abuse report filed.", postid=post.id)

@login_required
def r_removethread(request, thread_id):
    """ Move away (remove, hide, delete, censor) some thread.  """
    if not request.user.is_staff:
        raise PermissionError, "You should be an admin to do that."

    remcat_qs = Category.objects.filter(label=CAT_REMTHREADS_NAME)[:1]
    if not remcat_qs:
        raise HttpResponseServerError("Not configured to do that")
    remcat = remcat_qs[0]

    thr = get_object_or_404(Thread, pk=thread_id)
    thr.category = remcat
    thr.save()

    # Not RPCed, but still can use that:
    return r_getreturn(request, successtext="Thread moved away.",
      next=request.path)


## Base stuff.

@anonymous_login_required
def thread(request, thread_id):

    thr = get_object_or_404(Thread, pk=thread_id)

    if not thr.category.can_read(request.user):
        raise PermissionError, "You are not allowed to read this thread"

    render_dict = {}

    postform = PostForm()

    #if request.user.is_authenticated():
    #    render_dict.update({"watched": WatchList.objects.filter(user=request.user, thread=thr).count() != 0})

    # this must come after the post so new messages show up

    top_post = Post.objects.filter(thread=thread_id, depth=1)[0]
    # Get list of all replies.
    post_list = Post.get_children(top_post)  # Paginated by this list.

    ## sorting by last answer.
    if request.GET.get('sl', None) == '1':
        ### v1: unoptimal:
        #for post in post_list:
        #    post.last_answer_date = Post.get_tree(post).order_by("-date")[0].date
        #post_list = sorted(post_list, key=lambda p: p.last_answer_date, reverse=True)
        ### v2: SQLed.
        ## Not sure what 'ESCAPE' is meant to do here. Grabbed from
        ## treebeard queries:
        ##  cls.objects.filter(path__startswith=parent.path,
        ##  depth__gte=parent.depth)
        ## !! somewhat SQLite-specific (concat is '||')
        post_list = post_list.extra(select={
          "lastanswer": """SELECT date FROM snapboard_post AS child
            WHERE (child.path LIKE (snapboard_post.path || '%%') AND
              child.depth >= snapboard_post.depth)
            ORDER BY date DESC LIMIT 1 """
        }).order_by("-lastanswer")


    # Additional note: annotating watched posts in the tree can be done, for
    # example, by using 
    # WatchList.objects.filter(post__in=pl, user=request.user),
    # and, in the template, "{% post.id in watched_list %}".
    # (select related, '[wi.post.id for wi in ...]' and etc. might also be
    # needed).
    # This, of course, requires that post lists are retreived here in view,
    # rather than in the template.
    
    try:  # (totally optional)
        forum_name = Site.objects.get_current().name
    except Exception:  # whatever.
        forum_name = ""

    render_dict.update({
      'top_post': top_post,
      'post_list': post_list,
      'postform': postform,
      'thr': thr,
      'forum_name': forum_name,
    })
    
    return render_to_response('snapboard/thread',
      render_dict,
      context_instance=RequestContext(request, processors=extra_processors))


@anonymous_login_required
def post_reply(request, parent_id, thread_id=None, rpc=False):
    # thread_id paremeter was considered unnecessary here.
    # Although, '#thread_id/post_id_in_thread' might be preferrable to using
    # global post id.
    
    # with rpc=true returns dict with full form HTML.
    
    parent_post = get_object_or_404(Post, pk=int(parent_id))
    
    if request.POST and not rpc:  # POST HERE.
        thr = parent_post.thread
        if not thr.category.can_post(request.user):
            raise PermissionError, "You are not allowed to post in this thread"
        postform = PostForm(request.POST)
        if postform.is_valid():
            postobj = parent_post.add_child(
              thread=thr,
              user=request.user,
              text=postform.cleaned_data['text'],
            )
            postobj.save()
            postobj.notify()
            return success_or_reverse_redirect('snapboard_locate_post',
              args=(postobj.id,), req=request, msg="Posted successfully.")
    else:
        context = {'postform': PostForm(), 
          "parent_post": parent_post}
        if rpc:  # get form, not page.
            return {
              "html": render_to_string('snapboard/include/addpost.html',
                context, context_instance=RequestContext(request,
                  processors=extra_processors))
            }
        else:
            # ...non-JS reply form.
            return render_to_response('snapboard/post_reply',
              context, context_instance=RequestContext(request,
                processors=extra_processors))


@login_required
def edit_post(request, original, rpc=False):
    """ Edit an existing post.  """
    orig_post = get_object_or_404(Post, pk=int(original))
        
    if orig_post.user != request.user \
     or not orig_post.thread.category.can_post(request.user) \
     or not orig_post.thread.category.can_read(request.user):
        # Might be not in sync with the interface in thread.
        raise PermissionError, "You are not allowed to edit that."

    if request.POST and not rpc:
        # For editing: we modify the post in-place and save the previous
        # version into the separate model.
        post_rev = Post_revisions.make_from_post(orig_post)
        # ^^ a copy; not saved if not valid. vv might modify orig_post.
        # post_rev should get is 'previous' linking to the same
        #  object in Post_revisions
        postform = PostForm(request.POST, instance=orig_post)
        if postform.is_valid():
            post_rev.save()
            orig_post = postform.save(commit=False)
            orig_post.previous = post_rev
            orig_post.save()
        # else:  # ! XXX: errors? What errors?

        div_id_num = orig_post.id

        next = request.GET.get('next')
        if next:  # shouldn't happen with XMPP.
            return HttpResponseRedirect(next)
            #next.split('#')[0] + \
            #  '#snap_post' + str(orig_post.id))
        else:
            return success_or_reverse_redirect('snapboard_locate_post',
              args=(orig_post.id,), req=request, msg="Message updated.")
    else:  # get a form for editing.
        context = {'post': orig_post}
        if rpc:
            return {"html":
              render_to_string('snapboard/include/editpost.html',
                context, context_instance=RequestContext(
                  request, processors=extra_processors))
            }
        else:
            return render_to_response('snapboard/edit_post',
              context, context_instance=RequestContext(
                request, processors=extra_processors))


def show_revisions(request, post_id, rpc=False):
    """ Get all revisions of a specific post.  """
    orig_post = get_object_or_404(Post, pk=int(post_id))

    post = orig_post
    posts = [post]
    while post.previous:  # ! XXX: make tons of SQL queries.
        # (could probably make a single queryset of this; but not so
        # important)
        post = post.previous
        posts.append(post)
    posts = posts[::-1]  # up->down -- old->new

    if rpc:  # return JSONed data of all revisions.
        data = [{
          'text': post.text,
          'date': post.date,  # ! XXX: might not be saved. Check.
        } for post in posts]
        return data
    else:
        return render_to_response('snapboard/show_revisions',
          {'posts': posts, 'last_post': orig_post,
            'thread': orig_post.thread},
          context_instance=RequestContext(request,
            processors=extra_processors))


@anonymous_login_required
def new_thread(request, cat_id):
    """ Start a new discussion.  """
    category = get_object_or_404(Category, pk=cat_id)
    if not category.can_create_thread(request.user):
        raise PermissionError, "You cannost post in this category"

    if request.POST:
        threadform = ThreadForm(request.POST)
        if threadform.is_valid():
            # create the thread
            thread = Thread(
                    subject = threadform.cleaned_data['subject'],
                    category = category,
                    )
            thread.save()

            # create the post
            post = Post.add_root(
                    user = request.user,
                    thread = thread,
                    text = threadform.cleaned_data['post'],
                    )
            post.save()

            # redirect to new thread / return success message
            return success_or_reverse_redirect('snapboard_thread',
              args=(thread.id,), req=request, msg="Thread created.")
    else:
        threadform = ThreadForm()

    return render_to_response('snapboard/newthread',
            {
            'form': threadform,
            },
            context_instance=RequestContext(request, processors=extra_processors))


@login_required
def watchlist(request):
    """ This page shows the posts that have been marked as "watched" by the
    user.  """
    post_list = filter(lambda p: p.thread.category.can_view(request.user),
      [w.post for w in WatchList.objects.select_related(depth=3).filter(user=request.user)])
    # Pagination? Looks nice to allow in-url parameter like "?ppp=100".

    return render_to_response('snapboard/watchlist',
            {'posts': post_list},
            context_instance=RequestContext(request, processors=extra_processors))


@anonymous_login_required
def category_thread_index(request, cat_id):
    cat = get_object_or_404(Category, pk=cat_id)
    if not cat.can_read(request.user):
        raise PermissionError, "You cannot list this category"
    thread_list = Thread.view_manager.get_category(cat_id)
    render_dict = ({'title': ''.join((_("Category: "), cat.label)), 'category': cat, 'threads': thread_list})
    return render_to_response('snapboard/thread_index_categoryless',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))


def thread_index(request, num_limit=None, num_start=None):
    if request.user.is_authenticated():
        # filter on user prefs
        thread_list = Thread.view_manager.get_user_query_set(request.user)
    else:
        thread_list = Thread.view_manager.get_query_set()
    thread_list = filter(lambda t: t.category.can_view(request.user), thread_list)
    # ! This should be common with few more views, probably.
    if isinstance(request, XmppRequest):  # Apply Xmpp-specific limits  # ! TODO: request.is_xmpp() ?
        # ? int() failure would mean programming error... or not?
        num_start=int(num_start or 1)-1 # Starting from humanized '1'.
        num_limit=int(num_limit or 20)
        thread_list=thread_list[num_start:num_start+num_limit]
    render_dict = {'title': _("Recent Discussions"), 'threads': thread_list}
    return render_to_response('snapboard/thread_index',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))


def locate_post(request, post_id):
    """ Redirects to a post, given its ID.  """
    post = get_object_or_404(Post, pk=post_id)
    if not post.thread.category.can_read(request.user):
        raise PermissionError, "You cannot see it"
    # Count the number of visible posts before the one we are looking for, 
    # as well as the total
    #total = post.thread.count_posts(request.user)

    # ...everything is visible, threads paginated by first-level answers.
    # Looks funny, meh.
    root = post.get_root()
    # amount of paginated objects:
    total = root.get_children_count()

    settings = request.user.get_user_settings()
    ppp = settings.ppp
    if total < ppp:  # nowhere tp look for.
        page = 1
    else:
        # object amongst paginated we're looking for.
        answer = post.get_ancestors()[1] if post.depth > 2 else post
        # ...what; anyway, find the index number of the target object.
        # (not very nicely done, yes)
        # not sure about '+1' either.
        preceding_count = (i for i, x in enumerate(answer.get_siblings())
          if x == answer).next() + 1
        
        if settings.reverse_posts:
            page = (total - preceding_count - 1) // ppp + 1
        else:
            page = preceding_count // ppp + 1
    return HttpResponseRedirect('%s?page=%i#sp%i' % (reverse('snapboard_thread', args=(post.thread.id,)), page, post.id))


def category_index(request):
    return render_to_response('snapboard/category_index', {
      'cat_list': [c for c in Category.objects.all() if c.can_view(request.user)],
      },
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def edit_settings(request):
    """ Allow user to edit own profile.  Requires login.

    There are 4 buttons on this page: choose avatar, delete avatar, upload
    avatar, change settings.  """
    userdata, userdatacreated = UserSettings.objects.get_or_create(user=request.user)
    avatar, avatars = _get_avatars(request.user)
    if avatar:
        kwargs = {'initial': {'choice': avatar.id}}
    else:
        kwargs = {}
    settings_form, primary_avatar_form, upload_avatar_form = None, None, None
    # ! XXX: Actually, the avatars code was mostly copied from avatar/views.py
    # ! Which is problematic if avatar module is updated
    # ! but blends in much better.
    if request.method == 'POST':
        if 'updatesettings' in request.POST:  # Settings were edited.
            settings_form = UserSettingsForm(request.POST,
              instance=userdata, user=request.user)
            if settings_form.is_valid():
                settings_form.save(commit=True)
        elif 'avatar' in request.FILES:  # New avatar upload submitted.
            # Also 'avatarsubmit' in request.POST is assumed.
            upload_avatar_form = UploadAvatarForm(request.POST,
              request.FILES, user=request.user)
            if upload_avatar_form.is_valid():
                avatar = Avatar(user = request.user, primary = True)
                image_file = request.FILES['avatar']
                avatar.avatar.save(image_file.name, image_file)
                avatar.save()
                request.user.message_set.create(
                    message=_("Successfully uploaded a new avatar."))
                _notification_updated(request, avatar)
                return HttpResponseRedirect(request.path)  # (reload)
        elif 'choice' in request.POST:
            primary_avatar_form = PrimaryAvatarForm(request.POST,
              user=request.user, avatars=avatars, **kwargs)
            if primary_avatar_form.is_valid():  # Selection / deletion form.
                avatar = Avatar.objects.get(id=primary_avatar_form.cleaned_data['choice'])
                if 'defaultavatar' in request.POST:  # "choose" was pressed
                    # ! Maybe should check if it's the same avatar.
                    avatar.primary = True
                    avatar.save()
                    _notification_updated(request, avatar)
                    request.user.message_set.create(
                      message=_("Successfully updated your avatar."))
                    # No need for redirect here, seemingly.
                elif 'deleteavatar' in request.POST:  # "delete" was pressed
                    if unicode(avatar.id) == id and avatars.count() > 1:
                        # Find the next best avatar, and set it as the new primary
                        for a in avatars:
                            if unicode(a.id) != id:
                                a.primary = True
                                a.save()
                                _notification_updated(request, a)
                                break
                    avatar.delete()
                    request.user.message_set.create(
                      message=_("Deletion successful."))
                    return HttpResponseRedirect(request.path)  # (reload)
    # ! Create what was not created
    settings_form = settings_form or UserSettingsForm(None,
      instance=userdata, user=request.user)
    upload_avatar_form = upload_avatar_form or UploadAvatarForm(None,
      user=request.user)
    primary_avatar_form = primary_avatar_form or PrimaryAvatarForm(None,
      user=request.user, avatars=avatars, **kwargs)
    return render_to_response(
            'snapboard/edit_settings',
            {'settings_form': settings_form,
             'upload_avatar_form': upload_avatar_form,
             'primary_avatar_form': primary_avatar_form,
             'avatar': avatar,  'avatars': avatars, },
            context_instance=RequestContext(request, processors=extra_processors))


@login_required
def manage_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError, "What?"
    render_dict = {'group': group, 'invitation_form': InviteForm()}
    if request.GET.get('manage_users', False):
        render_dict['users'] = group.users.all()
    elif request.GET.get('manage_admins', False):
        render_dict['admins'] = group.admins.all()
    elif request.GET.get('pending_invitations', False):
        render_dict['pending_invitations'] = group.sb_invitation_set.filter(accepted=None)
    elif request.GET.get('answered_invitations', False):
        render_dict['answered_invitations'] = group.sb_invitation_set.exclude(accepted=None)
    return render_to_response(
            'snapboard/manage_group',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))


@login_required
def invite_user_to_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError, "What?"
    if request.method == 'POST':
        form = InviteForm(request.POST)
        if form.is_valid():
            invitee = form.cleaned_data['user']
            if group.has_user(invitee):
                invitation = None
                request.user.message_set.create(message=_('The user %s is already a member of this group.') % invitee)
            else:
                invitation = Invitation.objects.create(
                        group=group,
                        sent_by=request.user,
                        sent_to=invitee)
                request.user.message_set.create(message=_('A invitation to join this group was sent to %s.') % invitee)
            return render_to_response('snapboard/invite_user',
                    {'invitation': invitation, 'form': InviteForm(), 'group': group},
                    context_instance=RequestContext(request, processors=extra_processors))
    else:
        form = InviteForm()
    return render_to_response('snapboard/invite_user',
            {'form': form, 'group': group},
            context_instance=RequestContext(request, processors=extra_processors))


@login_required
def remove_user_from_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError, "What?"
    if request.method == 'POST':
        done = False
        user = User.objects.get(pk=int(request.POST.get('user_id', 0)))
        only_admin = int(request.POST.get('only_admin', 0))
        if not only_admin and group.has_user(user):
            group.users.remove(user)
            done = True
        if group.has_admin(user):
            group.admins.remove(user)
            send_notifications([user], 'group_admin_rights_removed',
              {'group': group})
            done = True
        if done:
            if only_admin:
                request.user.message_set.create(message=_('The admin rights of user %s were removed for the group.') % user)
            else:
                request.user.message_set.create(message=_('User %s was removed from the group.') % user)
        else:
            request.user.message_set.create(message=_('There was nothing to do for user %s.') % user)
    else:
        raise Http404, "Ain't here!"  # ?
    return HttpResponse('ok')


@login_required
def grant_group_admin_rights(request, group_id):
    """ """
    """ Although the Group model allows non-members to be admins, this view
    won"t let it.  """
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError, "What?"
    if request.method == 'POST':
        user = User.objects.get(pk=int(request.POST.get('user_id', 0)))
        if not group.has_user(user):
            request.user.message_set.create(message=_('The user %s is not a group member.') % user)
        elif group.has_admin(user):
            request.user.message_set.create(message=_('The user %s is already a group admin.') % user)
        else:
            group.admins.add(user)
            request.user.message_set.create(message=_('The user %s is now a group admin.') % user)
            send_notifications([user], 'group_admin_rights_granted',
              {'group': group})
            send_notifications(list(group.admins.all()), 'new_group_admin',
              {'new_admin': user, 'group': group})
    else:
        raise Http404, "Ain't here!"
    return HttpResponse('ok')


@login_required
def discard_invitation(request, invitation_id):
    if not request.method == 'POST':
        raise Http404, "Ain't here!"
    invitation = get_object_or_404(Invitation, pk=invitation_id)
    if not invitation.group.has_admin(request.user):
        raise PermissionError, "You can't!"
    was_pending = invitation.accepted is not None
    invitation.delete()
    if was_pending:
        request.user.message_set.create(message=_('The invitation was cancelled.'))
    else:
        request.user.message_set.create(message=_('The invitation was discarded.'))
    return HttpResponse('ok')


@login_required
def answer_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, pk=invitation_id, sent_to=request.user) # requires testing!
    form = None
    if request.method == 'POST':
        if invitation.accepted is not None:
            return HttpResponseRedirect('')
        form = AnwserInvitationForm(request.POST)
        if form.is_valid():
            if int(form.cleaned_data['decision']):
                invitation.group.users.add(request.user)
                invitation.accepted = True
                request.user.message_set.create(message=_('You are now a member of the group %s.') % invitation.group.name)
                send_notifications( list(invitation.group.admins.all()),
                  'new_group_member', {'new_member': request.user,
                  'group': invitation.group})
            else:
                invitation.accepted = False
                request.user.message_set.create(message=_('The invitation has been declined.'))
            invitation.response_date = datetime.datetime.now()
            invitation.save()
    elif invitation.accepted is None:
        form = AnwserInvitationForm()
    return render_to_response('snapboard/invitation',
            {'form': form, 'invitation': invitation},
            context_instance=RequestContext(request, processors=extra_processors))


## More XMPP stuff.
# ! XXX: Should be in xmppface.views, too.

@login_required
def xmppresourcify(request, resource=None, post_id=None):
    _log.debug("resourcify: user: %r" % request.user)
    post = _get_that_post(request, post_id)
    if not resource:
        resource="#%d-%d" % (post.id, post.thread.id)
    wl, created = WatchList.objects.get_or_create(user=request.user, post=post)
    wl.xmppresource = resource  # Just replace it.
    wl.save()
    # Do we need HTTP-availability of this? (can just use
    # success_or_reverse_redirect).
    return XmppResponse("okay.")


def xmpp_get_help(request, subject=None):
    """ Returns help message to the user, possibly on the specific subject.
    Can theoretically be used in the web view as well.  """
    subject = subject or "main"
    try:
        return render_to_response('snapboard/xmpp_help/%s'%subject, 
          None,
          context_instance=RequestContext(request,
            processors=extra_processors))
    except TemplateDoesNotExist:
        raise Http404, "No such help subject"


@login_required
def xmpp_web_login_cmd(request):
    """ Lets XMPP users log in into the web without using any password. 
    Uses the 'loginurl' django app.  """
    import loginurl.utils
    current_site = Site.objects.get_current()
    key = loginurl.utils.create(request.user)
    url = u"http://%s%s" % (
      unicode(current_site.domain),
      reverse('loginurl_login', kwargs={'key': key.key}),
    )
    # * note that this reverse() requires quite a hack as of loginurl 0.1.3
    return XmppResponse('Login url: <a href="%s">%s</a> .' % (url, url))


@login_required
def xmpp_web_changepw(request, password=''):
    """ Change (or set) user's password for web login.  Can be empry
    (effectively disabling logging in with pasword).  """
    # JID is supposedly trusted and can *just* change it.
    request.user.set_password(password)
    if password:
        return XmppResponse("Password changed.")
    else:
        return XmppResponse("Password disabled.") 


@login_required
def xmpp_unregister_cmd(request):
    """ Disassociate (log off?) JID from the user.  """
    # ! XXX: Should check if password is empty?
    request.user.sb_usersettings.jid = None
    return XmppResponse("Goodbye, %r." % request.user.username) 


## ...

# RPC information with previous functions.
RPC_OBJECT_MAP = {
        "thread": Thread,
        "post": Post,
        }

RPC_ACTION_MAP = {
        "censor": rpc_censor,
        "gsticky": rpc_gsticky,
        "csticky": rpc_csticky,
        "close": rpc_close,
        "abuse": r_abusereport,
        "watch": r_watch_post,
        "quote": rpc_quote,
        "geteditform": edit_post,
        "getreplyform": post_reply,
        "getrevisions": show_revisions,
        }
# Temporary list of RPC functions coverted to advanced action handers.
RPC_AACTIONS = ["watch", "abuse", "geteditform", "getreplyform", "getrevisions"]


def _brand_view(func):
    """ Mark a view as belonging to SNAPboard.

    Allows the UserBanMiddleware to limit the ban to SNAPboard in larger
    projects.  """
    setattr(func, '_snapboard', True)

_brand_view(rpc)
_brand_view(thread)
_brand_view(edit_post)
_brand_view(new_thread)
_brand_view(watchlist)
_brand_view(category_thread_index)
_brand_view(thread_index)
_brand_view(locate_post)
_brand_view(category_index)
_brand_view(edit_settings)
_brand_view(manage_group)
_brand_view(invite_user_to_group)
_brand_view(remove_user_from_group)
_brand_view(grant_group_admin_rights)
_brand_view(discard_invitation)
_brand_view(answer_invitation)
_brand_view(xmpp_get_help)
_brand_view(xmpp_register_cmd)

# vim: ai ts=4 sts=4 et sw=4
