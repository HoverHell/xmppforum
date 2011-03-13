""" Views for the forum.  """

import logging
import datetime
import time

from django import forms
from django.conf import settings
from django.contrib.auth import decorators
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import connection, transaction
from django.db.models import Q, Count
from django.http import (HttpResponse, HttpResponseRedirect, Http404,
  HttpResponseServerError)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect

# For easy notification resource handling:
from notification import models as notification

import re

#from django.contrib.auth.decorators import login_required
# XmppFace
import xmppface.xmppbase
from xmppface.xmppbase import (XmppRequest, XmppResponse, render_to_response,
 success_or_redirect, success_or_reverse_redirect)
from xmppface.xmppstuff import send_notifications
from xmppface import forms as xfforms
from xmppface.views import login_required

from anon.decorators import anonymous_login_required

# Avatar form in UserSettings


from snapboard.forms import *
from snapboard.models import *
from snapboard.models import (AnonymousUser, get_flathelper_list,
  get_adv_annotated_list)
from snapboard.util import *


_log = logging.getLogger('snapboard.views')


CAT_REMTHREADS_NAME = getattr(settings, 'CAT_REMTHREADS_NAME',
  'Removed Threads')


## Get and save the site name (or URL) for the further use.
try:  # (totally optional)
    CURRENT_SITE = Site.objects.get_current()
    SITE_NAME = CURRENT_SITE.name
    SITE_DOMAIN = CURRENT_SITE.domain
except Exception:  # whatever.  XMPP links won't work though.
    SITE_NAME = ""
    SITE_DOMAIN = ""


def snapboard_default_context(request):
    """ Provides some default information for all templates.

    This should be added to the settings variable
    TEMPLATE_CONTEXT_PROCESSORS """
    return {
      'SNAP_MEDIA_PREFIX': SNAP_MEDIA_PREFIX,
      'SNAP_POST_FILTER': SNAP_POST_FILTER,
      'LOGIN_URL': settings.LOGIN_URL,
      'LOGOUT_URL': settings.LOGOUT_URL,
      'SITE_NAME': SITE_NAME,
      'SITE_DOMAIN': SITE_DOMAIN,
      }


def user_settings_context(request):
    return {'user_settings': request.user.get_user_settings()}


def timedelta_now_context(request):
    """ A somewhat weird context processor that adds now() into the context
    so it can be called exactly once per request.  """
    return {'now': time.mktime(datetime.datetime.now().timetuple())}


extra_processors = [user_settings_context, snapboard_default_context,
  timedelta_now_context]


def _get_that_post(request, post_form_id=None, post_id=None):
    """ Helper function for allowing post-related commands unto unspecified
    "last notified" post.  Raises Http404 if cannot.

    Depends on django cache database."""
    if post_form_id:
        return Post.get_post_or_404(post_form_id)
    elif post_id:
        return get_object_or_404(Post, pk=post_id)

    # otherwise - find one!  (should not happen with HTTP though)
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
            raise Http404("Dunno such. Must've vanished. Specify precise post.")
    else:
        raise Http404("Dunno any. Specify precise post.")


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


def rpc_dispatch(request):
    """ Delegates simple rpc requests (which usually come over HTTP form
    javascripts.  """
    if not request.POST:
        return HttpResponseServerError("RPC data is absent")

    response_dict = {}

    try:
        action = request.POST['action'].lower()
        rpc_func = RPC_ACTION_MAP[action]
    except KeyError:
        return HttpResponseServerError("RPC: Unknown RPC function")

    try:
        oid = int(request.POST['oid'])
    except KeyError:
        return HttpResponseServerError("RPC: missing oid.")

    # Note: django's exception handling is used.
    # Dict is expected for rpc=True call of the view.
    response = rpc_func(request, oid, rpc=True)
    response_dict.update(response)
    return HttpResponse(simplejson.dumps(response_dict),
      mimetype='application/javascript')


@login_required
def r_watch_post(request, post_form_id=None, post_id=None, resource=None,
  rpc=False):
    post = _get_that_post(request, post_form_id, post_id)
    # ^ 'auto' fetching should only be done from XMPP.
    thr = post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError("You are not allowed to do that")
    try:
        ## ! XXX: This doesn't look very good.
        ## ? Check if user's already subscribed to that branch?
        # (post__in get_ancestors)
        ## Problem is, user might want to unsubscribe from whatever
        # subscription caused the last notification. But then, such action
        # would be better explicit (or with confirmation).
        ## Another possibility is to create UnwatchList which allows to
        # ignore notifications from specific branches of a subscribed
        # subtree.
        wl = WatchList.objects.get(user=request.user, post=post)
        # it exists, stop watching it
        wl.delete()
        return r_getreturn(request, rpc, {'link':_('watch'),
          'msg':_('This thread has been removed from your favorites.')},
          "Watch removed.", postid=post.id)
    except WatchList.DoesNotExist:
        # create it
        wl = WatchList(user=request.user, post=post, xmppresource=resource)
        wl.save()
        return r_getreturn(request, rpc, {'link':_('dont watch'),
          'msg':_('This thread has been added to your favorites.')},
          "Watch added.", postid=post.id)


#@userbannable
@login_required
def r_abusereport(request, post_id=None, rpc=False):
    """ Report some inappropriate post for the admins to consider censoring.
    """
    post = get_object_or_404(Post, pk=post_id)
    thr = post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError("You are not allowed to do that")
    abuse, created = AbuseReport.objects.get_or_create(
      submitter = request.user,
      post = post,
      )
    return r_getreturn(request, rpc, {
       'link': '',
       'msg': _('The moderators have been notified of possible abuse')},
      "Abuse report filed.", postid=post.id)


@staff_required
def r_removethread(request, thread_id):
    """ Move away (remove, hide, delete, censor) some thread.  """
    remcat_qs = Category.objects.filter(label=CAT_REMTHREADS_NAME)[:1]
    if not remcat_qs:
        return HttpResponseServerError("Not configured to do that")
    remcat = remcat_qs[0]

    thr = get_object_or_404(Thread, pk=thread_id)
    thr.category = remcat
    thr.save()

    # Not RPCed, but still can use that:
    return r_getreturn(request, successtext="Thread moved away.")


## ? XXX: move somewhere else?
def _get_for_state(state, source, default=None):
    """ Small helper function for getting some data from @param source
    depending on state.  """
    try:
        if isinstance(source, tuple):
            return source[0] if state else source[1]
        if callable(source):
            return source(state)
        return default
    except Exception, exc:
        # ! XXX: Logging?
        return None


def rpc_gettoggler(objclass, field, wrap_with=staff_required,
  rpcreturn=None, xmppreturn=None):
    """ A generator function which creates a view for toggling some field
    over http/rpc/xmpp.  Uses staff_required by default.

    rpcreturn is function of state that returns data to be JSONed to the RPC
    client.  """
    def _toggle_that(request, oid=None, rpc=False, state=None):
        obj = get_object_or_404(objclass, pk=oid)
        if state is not None:
            state = bool(state)  # set to the specified state.
        else:
            state = not (getattr(obj, field, True))  # toggle it.
        setattr(obj, field, state)  # do it, actually.
        obj.save()
        # ... and compute the ultimate return.
        rpcdata = _get_for_state(state, rpcreturn, default={})
        xmppdata = _get_for_state(state, xmppreturn)
        postid = obj.id if objclass == Post else None
        return r_getreturn(request, rpc, rpcdata=rpcdata,
          successtext=xmppdata, postid=postid)
    return wrap_with(_toggle_that)  # staff required by default.


# Over HTTP/RPC/XMPP we get an 'id' argument (passed to the view),
# and an implicit (object, field) pair (which is set in the function).
r_set_gsticky = rpc_gettoggler(Thread, 'gsticky', rpcreturn=(
    {'link':_('unset gsticky'),
     'msg':_('This thread is now globally sticky.')},
    {'link':_('set gsticky'),
     'msg':_('Removed thread from global sticky list')}
    )
  )

r_set_csticky = rpc_gettoggler(Thread, 'csticky', rpcreturn=(
    {'link':_('unset csticky'),
     'msg':_('This thread is sticky in its category.')},
    {'link':_('set csticky'),
     'msg':_('Removed thread from category sticky list')}
    )
  )

r_set_close = rpc_gettoggler(Thread, 'closed', rpcreturn=(
    {'link':_('open thread'), 'msg':_('This discussion is now CLOSED.')},
    {'link':_('close thread'), 'msg':_('This discussion is now OPEN.')}
    )
  )

r_set_censor = rpc_gettoggler(Post, 'censor', rpcreturn=(
    {'link':_('uncensor'), 'msg':_('This post is censored!')},
    {'link':_('censor'), 'msg':_('This post is no longer censored.')}
    )
  )


## Base stuff.

#@userbannable
@anonymous_login_required
def thread(request, thread_id):
    """ Render a particular thread starting from its root post.  """
    ## ! XXX: might be unnecessary.
    #thr = get_object_or_404(Thread, pk=thread_id)

    top_post = get_object_or_404(Post.objects.select_related(),
      thread=thread_id, depth=1)
    return thread_post(request, post=top_post, subtopic=False)


@anonymous_login_required
def thread_post(request, post_id=None, post_form_id=None, post=None,
  depth="v", subtopic=True):
    """ Renders (part of) the thread starting from the specified post.
    Passes the `subtopic` parameter to the template, which annotates it with
    "Showing a part of the thread" message. """

    if post is not None:
        top_post = post
    elif post_id is not None or post_form_id is not None:
        top_post = _get_that_post(request, post_form_id, post_id)
    else:  # should not ever happen.
        _log.error("Invalid invocation of the thread_post.")
        import traceback
        _log.debug("".join(traceback.print_stack()))
        return HttpResponseServerError()

    thr = top_post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError("You are not allowed to read this thread")

    render_dict = {}

    ## Helper for retreiving int values from request.GET
    def l_getintparam(param, default=''):
        prm = request.GET.get(param, '')
        ## callable is allowed for slight optimization.
        return int(prm) if prm.isdigit() \
          else (default() if callable(default) else default)

    l_str2int = lambda x: Post._str2int(x)
    l_int2str = lambda v: Post._int2str(v).rjust(Post.steplen, '0')
    l_getinterval = lambda parent, left, right: (parent + l_int2str(left + 1),
      parent + l_int2str(right + 1))  # starts from '1', apparently.

    ### Pagination (mildly obsolete):
    ## overridable ppp.
    ppp = l_getintparam('ppp', lambda: request.user.get_user_settings().ppp)
    from django.core.paginator import Paginator, InvalidPage
    paginator = Paginator(SliceHack(), ppp)
    # This might be problematic if some posts got deleted/moved.
    # Bit more safe way (but not completely good either) would be something
    # like
    # paginator._count = \
    #   l_str2int(top_post.get_children().reverse()[:1].path[-Post.steplen]
    # (with consideration for empty children QS).
    paginator._count = top_post.get_children_count()
    page_obj = paginator.page(request.GET.get("page", 1))
    slice = page_obj.object_list.slice
    # -1 because last gets included too this way.
    pinterval = l_getinterval(top_post.path, slice.start, slice.stop - 1)

    maxdepthd = l_getintparam('md', 28)
    nfsib = l_getintparam('nfsib', None)  # full next siblings

    # TODO: can find it dynamically (and then cache)!
    maxdepth = top_post.depth + maxdepthd
    #qs = Post.objects.filter(
    fsibpath = None
    if nfsib:  # 1. show fully target post and few next siblings.
        parentpath = top_post.path[:-Post.steplen]
        tpnum = l_str2int(top_post.path[-Post.steplen:])
        fsibpath = parentpath + l_int2str(tpnum + nfsib)  # some further sibling.
        qs = Post.objects.filter(
          path__range=(
            top_post.path,
            fsibpath
            )
          )
    else:
        qs = top_post.get_descendants()
    qs = qs.filter(
       thread=thr,
       #depth__gte=top_post.depth,
       depth__lte=maxdepth,
      )
    qs = qs.annotate(
       abuse=Count('sb_abusereport_set')
      ).extra(
       select={
        "numanswers": """CASE WHEN snapboard_post.depth = %d THEN
          (SELECT COUNT(*) FROM snapboard_post AS child WHERE (
            child.path LIKE (snapboard_post.path || '%%%%') AND
            child.depth > snapboard_post.depth
          ))
          ELSE "" END
        """ % maxdepth,
        # "abuse": 0,
       }
      ).select_related(depth=1
      ## A problem: .only() or .defer() together with .select_related()
      ## significantly increase query's execution time.
      #).only(
      #  'depth', 'texth', 'date', 'censor', 'freespeech', 'previous',
      #  'tlid', 'user__username', 'user__is_staff'
      #.defer(
      #  'text', 'path', 'thread', 'ip',
      #).select_related(depth=1)
      )

    # ! XXX: temporary hack?
    top_post.abuse = top_post.sb_abusereport_set.count()

    sibqs = fsibqs = None
    nsib = l_getintparam('nsib', None)  # next siblings, short.
    ## full query on nfsib; push away nsib's paths.
    if nsib:
        sibqs = top_post.get_siblings(
          ).filter(
            thread=thr,
            path__gt=(fsibpath if fsibpath else top_post.path)
          ).annotate(
            abuse=Count('sb_abusereport_set')
          ).extra(
            select={
             "numanswers": """
               SELECT COUNT(*) FROM snapboard_post AS child WHERE (
                 child.path LIKE (snapboard_post.path || '%%%%') AND
                 child.depth > snapboard_post.depth
               )""",
             "nsib": "1",
            }
          ).select_related(depth=1
          )
        sibqs = sibqs[:nsib]

    ## Only enable pagination filtering if a page is specified.
    ## (Can grab a specific page if willing.)
    if request.GET.get('page', ''):
        qs = qs.filter(path__range=pinterval,)

    # finally, retreive and annotate the result.
    if subtopic:
        listdepth = top_post.depth
        qsl = list(qs)  # grab the data.
        res = [top_post] + qsl  # resulting page tree.
        if request.GET.get('nav', None) == '1':
            top_post.nav = True
            top_post.n_down = top_post.get_next_sibling()
            top_post.n_up = top_post.get_prev_sibling()
            ancestors = top_post.get_ancestors(
              ).filter(depth__gte=2  # avoid the main post in there
              ).annotate(abuse=Count('sb_abusereport_set')
              ).reverse()
            top_post.n_left = ancestors[0] if ancestors.exists() else None
            # if len(ancestors) == 1:
            # / if depth = 2:
            #  top_post.n_left = "thr".
            top_post.n_right = qsl[0] if qsl else None
            ma = request.GET.get('ma', None)  # max. ancestors.
            if ma is not None and ma.isdigit():
                ma = int(ma)
                res = list(ancestors[:ma])[::-1] + res
            else:
                res = list(ancestors)[::-1] + res
        if nsib:
            res = res + list(sibqs)
        post_list = get_flathelper_list(qs=res)
        top_post.is_flat = False  # fixit.
        #top_post = None  # there ain't no top_post in here!..  But not a problem, okay.
        # (and actually can show it; but probably don't need)
    else:
        ## sorting by last answer.
        ## ! Might not make any sense right now.
        if request.GET.get('sl', None) == '1':
            ### v1: unoptimal:
            #for post in post_list:
            #    post.last_answer_date = \
            #      Post.get_tree(post).order_by("-date")[0].date
            #post_list = sorted(post_list, key=lambda p: p.last_answer_date,
            # reverse=True)
            ### v2: SQLed.
            ## Not sure what 'ESCAPE' is meant to do here. Grabbed from
            ## treebeard queries:
            ##  cls.objects.filter(path__startswith=parent.path,
            ##  depth__gte=parent.depth)
            ## !! XXX: somewhat SQLite-specific (concat is '||')
            ##  XXX: Move into the model manager?
            post_list = post_list.extra(select={
              "lastanswer": """SELECT date FROM snapboard_post AS child
                WHERE (child.path LIKE (snapboard_post.path || '%%') AND
                  child.depth >= snapboard_post.depth)
                ORDER BY date DESC LIMIT 1 """
            }).order_by("-lastanswer")

        post_list = get_flathelper_list(qs=qs)
        #qs = qs[1:]  # was necessary for skipping top_post in its get_tree.
        # Get list of all replies.
        #post_list = Post.get_children(top_post)  # Paginated by this list.
        listdepth = 2

    # Additional note: annotating watched posts in the tree can be done, for
    # example, by using
    # WatchList.objects.filter(post__in=pl, user=request.user),
    # and, in the template, "{% post.id in watched_list %}".
    # (select related, '[wi.post.id for wi in ...]' and etc. might also be
    # needed).
    # This, of course, requires that post lists are retreived here in view,
    # rather than in the template.

    render_dict.update({
      'top_post': top_post,
      'post_list': post_list,
      'thr': thr,
      'paginator': paginator,
      'page_obj': page_obj,
      'subtopic': subtopic,
      'listdepth': listdepth,  # at which depth the post_list is.
      'maxdepth': maxdepth,
    })

    return render_to_response('snapboard/thread',
      render_dict,
      context_instance=RequestContext(request, processors=extra_processors))


def thread_latest(request, thread_id, num_posts=10):
    """ Show last (newest) posts in the specified thread.  """
    thr = get_object_or_404(Thread, pk=thread_id)
    if not thr.category.can_read(request.user):
        raise PermissionError("You are not allowed to read this thread")

    post_list = Post.objects.filter(thread=thread_id).order_by("-odate"
      ).select_related(depth=2)
    # ! XXX: sqlite-specific concat.
    basesub = """SELECT %s FROM snapboard_post AS xparent WHERE
      snapboard_post.path LIKE xparent.path || '%%%%' AND xparent.depth =
      (snapboard_post.depth - 1) """
    ### v1: make lots of queries.
    #for post in post_list:
    #    post.parent = post.get_parent()
    ### v2: make one subquery for each extra field, inconveniently.
    #post_list.extra(select={"parent_text": basesub % "text",
    #  "parent_user": basesub % "user_id", })
    ### v3: make two queries and reconstruct stuff.
    post_list = post_list.extra(select={"parent_id": basesub % "id"})
    post_list = post_list[:num_posts]  # take a slice, finally.
    parents = [post.parent_id for post in post_list]
    parent_list = Post.objects.filter(
      id__in=parents).select_related(depth=2)
    parent_dict = dict([(post.id, post) for post in parent_list])
    for post in post_list:
        post.parent = parent_dict.get(post.parent_id, None)
    post_list = post_list[::-1]  # from older to newer.

    return render_to_response('snapboard/thread_latest',
      {'post_list': post_list, 'thr': thr, },
      context_instance=RequestContext(request, processors=extra_processors))


def _redirect_to_posts(target1, target2=None):
    res = reverse('snapboard_thread_post',
      args=(target1.id,),)
    if target2:
        res += u'#%s' % target2.id_form_m
    return res


#@userbannable
@anonymous_login_required
def post_reply(request, post_form_id=None, post_id=None, rpc=False):
    # with rpc=true returns dict with full form HTML.
    parent_post = _get_that_post(request, post_form_id, post_id)

    if request.POST and not rpc:  # POST HERE.
        thr = parent_post.thread
        if not thr.category.can_post(request.user) or thr.closed:
            raise PermissionError(u"You are not allowed to post "
              u"in this thread")
        postform = PostForm(request.POST)
        if postform.is_valid():
            postobj = parent_post.add_child(
              thread=thr,
              user=request.user,
              **(postform.cleaned_data))  # text and whatnot.
            postobj.save()
            postobj.notify()
            return success_or_redirect(request,
              _redirect_to_posts(parent_post, postobj),
              u"Posted successfully.")
        else:
            pass  # ???
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


#@userbannable
@login_required
def edit_post(request, post_form_id=None, post_id=None, rpc=False):
    """ Edit an existing post.  """
    # with rpc=true returns dict with full form HTML.
    orig_post = _get_that_post(request, post_form_id, post_id)

    if orig_post.user != request.user \
     or not orig_post.thread.category.can_post(request.user) \
     or not orig_post.thread.category.can_read(request.user) \
     or orig_post.thread.closed:
        # Might be not in sync with the interface in thread.
        raise PermissionError("You are not allowed to edit that.")

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

        return r_getreturn(request, rpc=False,
          successtext="Message updated.", postid=orig_post.id)
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


def show_revisions(request, post_form_id=None, post_id=None, rpc=False):
    """ Get all revisions of a specific post.  """
    orig_post = _get_that_post(request, post_form_id, post_id)

    post = orig_post
    posts = [post]
    while post.previous:  # ! XXX: make tons of SQL queries.
        # (could probably make a single queryset of this; but not so
        # important)
        post = post.previous
        posts.append(post)
    posts = posts[::-1]  # up->down -- old->new

    ## Diff v2:
    prev_post = None
    for post in posts:
        if prev_post is not None:
            post.difflist = diff_posts(prev_post, post)
        prev_post = post

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


#@userbannable
@anonymous_login_required
def new_thread(request, cat_id):
    """ Start a new discussion.  """
    warn = None

    threadform = ThreadForm(request.user,
      request.POST if request.POST else None,
      initial={'category': cat_id})  # will be selected if it's there.
    postform = PostForm(request.POST if request.POST else None)

    if request.POST:
        if threadform.is_valid() and postform.is_valid():
            cat_id = threadform.cleaned_data.pop('category')
            category = get_object_or_404(Category, pk=cat_id)
            if not category.can_create_thread(request.user):
                raise PermissionError("You cannost post in this category")

            ## To make sure no postless threads remain.
            #with transaction.commit_on_success():  ## django1.3 required :(

            @transaction.commit_on_success
            def make_thread():
                nthread = Thread(
                  category=category,
                  #subject=threadform.cleaned_data['subject'],
                  **(threadform.cleaned_data))
                nthread.save()
                # create the post
                rpost = Post.add_root(
                  user=request.user,
                  thread=nthread,
                  **(postform.cleaned_data))
                rpost.save()
                return nthread, rpost

            nthread, rpost = make_thread()
            # redirect to new thread / return success message
            return success_or_reverse_redirect('snapboard_thread',
              args=(nthread.id,), req=request, msg="Thread created.")
    else:
        ## Warn the user if there's a problem with supplied category.
        if cat_id is not None:  # A specific category was supplied in URL.
            try:
                category = Category.objects.get(pk=cat_id)
            except Category.DoesNotExist:
                warn = ("Unknown category was supplied."
                  " Select one from the list.")
            else:
                if not category.can_create_thread(request.user):
                    warn = ("You cannot post in the supplied category."
                      " You still can select one from the list.")

    return render_to_response('snapboard/newthread',
      {'threadform': threadform,
       'postform': postform,
       'warn': warn},
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def watchlist(request):
    """ This page shows the posts that have been marked as "watched" by the
    user.  """
    post_list = [
       w.post for w in
        WatchList.objects.select_related(depth=3).filter(user=request.user)
       if w.post.thread.category.can_view(request.user)]
    # Pagination? Looks nice to allow in-url parameter like "?ppp=100".

    return render_to_response('snapboard/watchlist',
      {'posts': post_list},
      context_instance=RequestContext(request, processors=extra_processors))


def _thread_annotate_posts(thread_list):
    """ Requests threads' first and last posts and puts them under the same
    names.  Mutates thread_list.  """
    ## Not sovery optimal, but don't know a much better way.
    last_posts = [t.last_post for t in thread_list]
    first_posts = [t.first_post for t in thread_list]
    posts = Post.objects.filter(pk__in=(last_posts+first_posts)
      ).select_related()
    postsd = dict([(p.id, p) for p in posts])
    for t in thread_list:
        t.last_post = postsd.get(t.last_post, None)
        t.first_post = postsd.get(t.first_post, None)
    return thread_list


@anonymous_login_required
def category_thread_index(request, cat_id):
    cat = get_object_or_404(Category, pk=cat_id)
    if not cat.can_read(request.user):
        raise PermissionError("You cannot list this category")
    thread_list = Thread.view_manager.get_category(cat_id)
    thread_list = _thread_annotate_posts(thread_list)
    render_dict = ({'title': ''.join((_("Category: "), cat.label)),
      'category': cat, 'threads': thread_list})
    return render_to_response('snapboard/thread_index_categoryless',
      render_dict,
      context_instance=RequestContext(request, processors=extra_processors))


@anonymous_login_required
def thread_index(request, num_limit=None, num_start=None,
  template_name='snapboard/thread_index'):
    if request.user.is_authenticated():
        # filter on user prefs
        thread_list = Thread.view_manager.get_user_query_set(request.user)
    else:
        thread_list = Thread.view_manager.get_query_set()
    thread_list = [t for t in thread_list
      if t.category.can_view(request.user)]
    # Extra annotations.
    thread_list = _thread_annotate_posts(thread_list)
    # ! This should be common with few more views, probably.
    if request.is_xmpp():  # Apply Xmpp-specific limits
        # ? int() failure would mean programming error... or not?
        num_start = int(num_start or 1) - 1  # Starting from humanized '1'.
        num_limit = int(num_limit or 20)
        thread_list = thread_list[num_start:num_start + num_limit]
    render_dict = {'title': _("Recent Discussions"), 'threads': thread_list}
    return render_to_response(template_name,
      render_dict,
      context_instance=RequestContext(request, processors=extra_processors))


@anonymous_login_required
def category_index(request, template_name='snapboard/category_index'):
    return render_to_response(template_name, {
      'cat_list': [c for c in Category.objects.all()
        if c.can_view(request.user)],
      },
      context_instance=RequestContext(request, processors=extra_processors))


@anonymous_login_required
def merged_index(request):
    """ Outputs a page with both thread_index and category_index on it.  """
    ## XXX: Okay, this is NOT good.
    catresp = category_index(request,
      template_name='snapboard/include/category_index')
    cathtml = getattr(catresp, 'content', '')
    thrresp = thread_index(request,
      template_name='snapboard/include/thread_index')
    thrhtml = getattr(thrresp, 'content', '')
    return render_to_response('snapboard/merged_index',
      {'category_index': cathtml, 'thread_index': thrhtml},
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def edit_settings(request):
    """ Allow user to edit own profile.  Requires login.

    There are 4 buttons on this page: choose avatar, delete avatar, upload
    avatar, change settings.  """
    userdata, userdatacreated = \
      UserSettings.objects.get_or_create(user=request.user)
    xfuserdata, xfuserdatacreated = \
      xfforms.UserSettings.objects.get_or_create(user=request.user)
    # ! XXX: Actually, the avatars code was mostly copied from avatar/views.py
    #  Which is problematic if avatar module is updated
    #  but blends in much better.
    from avatar.models import Avatar, avatar_file_path
    from avatar.forms import PrimaryAvatarForm, UploadAvatarForm
    import avatar.views
    uavatar, avatars = avatar.views._get_avatars(request.user)
    if uavatar:
        kwargs = {'initial': {'choice': uavatar.id}}
    else:
        kwargs = {}
    settings_form = xfsettings_form = primary_avatar_form = \
      upload_avatar_form = None
    if request.method == 'POST':
        if 'updatesettings' in request.POST:  # Settings were edited.
            settings_form = UserSettingsForm(request.POST,
              instance=userdata, user=request.user)
            xfsettings_form = xfforms.UserSettingsForm(request.POST,
              instance=xfuserdata, user=request.user)
            if settings_form.is_valid():
                settings_form.save(commit=True)
            # ! I don't see very much of a problem if only one is valid.
            if xfsettings_form.is_valid():
                xfsettings_form.save(commit=True)
        elif 'avatar' in request.FILES:  # New avatar upload submitted.
            return avatar.views.add(request, next_override=request.path)
        elif 'choice' in request.POST:
            # This part was rewritten to use the same form for choosing the
            # default and deleting, i.e. using single choice for both
            # instead of multiple choice for deleteavatar.
            primary_avatar_form = PrimaryAvatarForm(request.POST,
              user=request.user, avatars=avatars, **kwargs)
            if primary_avatar_form.is_valid():  # Selection / deletion form.
                savatar = get_object_or_404(Avatar,
                  id=primary_avatar_form.cleaned_data['choice'])
                if 'defaultavatar' in request.POST:  # "choose" was pressed
                    # ! Maybe should check if it's the same avatar.
                    savatar.primary = True
                    savatar.save()
                    avatar.views._notification_updated(request, savatar)
                    request.user.message_set.create(
                      message=_("Successfully updated your avatar."))
                    # No need for redirect here, seemingly.
                elif 'deleteavatar' in request.POST:  # "delete" was pressed
                    if unicode(uavatar.id) == id and avatars.count() > 1:
                        # Find the next best avatar, and set it as the new
                        # primary
                        for av in avatars:
                            if unicode(av.id) != id:
                                av.primary = True
                                av.save()
                                avatar.views._notification_updated(
                                  request, av)
                                break
                    savatar.delete()
                    request.user.message_set.create(
                      message=_("Deletion successful."))
                    return HttpResponseRedirect(request.path)  # (reload)
    # ! Create what was not created; cannot create all of them always
    #  because most of them will fail validation then.
    settings_form = settings_form or UserSettingsForm(None,
      instance=userdata, user=request.user)
    xfsettings_form = xfsettings_form or xfforms.UserSettingsForm(None,
      instance=xfuserdata, user=request.user)
    upload_avatar_form = upload_avatar_form or UploadAvatarForm(None,
      user=request.user)
    primary_avatar_form = primary_avatar_form or PrimaryAvatarForm(None,
      user=request.user, avatars=avatars, **kwargs)
    return render_to_response(
      'snapboard/edit_settings',
      {'settings_form': settings_form,
       'xfsettings_form': xfsettings_form,
       'upload_avatar_form': upload_avatar_form,
       'primary_avatar_form': primary_avatar_form,
       'avatar': avatar,  'avatars': avatars, },
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def manage_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError("What?")
    render_dict = {'group': group, 'invitation_form': InviteForm()}
    if request.GET.get('manage_users', False):
        render_dict['users'] = group.users.all()
    elif request.GET.get('manage_admins', False):
        render_dict['admins'] = group.admins.all()
    elif request.GET.get('pending_invitations', False):
        render_dict['pending_invitations'] = \
          group.sb_invitation_set.filter(accepted=None)
    elif request.GET.get('answered_invitations', False):
        render_dict['answered_invitations'] = \
          group.sb_invitation_set.exclude(accepted=None)
    return render_to_response(
      'snapboard/manage_group',
      render_dict,
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def invite_user_to_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError("What?")
    if request.method == 'POST':
        form = InviteForm(request.POST)
        if form.is_valid():
            invitee = form.cleaned_data['user']
            if group.has_user(invitee):
                invitation = None
                request.user.message_set.create(message=_('The user %s is '
                  'already a member of this group.') % invitee)
            else:
                invitation = Invitation.objects.create(group=group,
                  sent_by=request.user, sent_to=invitee)
                request.user.message_set.create(message=_('A invitation to '
                  'join this group was sent to %s.') % invitee)
            return render_to_response('snapboard/invite_user',
              {'invitation': invitation, 'form': InviteForm(),
               'group': group},
              context_instance=RequestContext(request,
               processors=extra_processors))
    else:
        form = InviteForm()
    return render_to_response('snapboard/invite_user',
      {'form': form, 'group': group},
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def remove_user_from_group(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError("What?")
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
                request.user.message_set.create(
                  message=_('The admin rights of user %s were removed for '
                    'the group.') % user)
            else:
                request.user.message_set.create(
                  message=_('User %s was removed from the group.') % user)
        else:
            request.user.message_set.create(
              message=_('There was nothing to do for user %s.') % user)
    else:
        raise Http404("Ain't here!")  # ?
    return HttpResponse('ok')


@login_required
def grant_group_admin_rights(request, group_id):
    """ """
    """ Although the Group model allows non-members to be admins, this view
    won"t let it.  """
    group = get_object_or_404(Group, pk=group_id)
    if not group.has_admin(request.user):
        raise PermissionError("What?")
    if request.method == 'POST':
        user = User.objects.get(pk=int(request.POST.get('user_id', 0)))
        if not group.has_user(user):
            request.user.message_set.create(
              message=_('The user %s is not a group member.') % user)
        elif group.has_admin(user):
            request.user.message_set.create(
              message=_('The user %s is already a group admin.') % user)
        else:
            group.admins.add(user)
            request.user.message_set.create(
              message=_('The user %s is now a group admin.') % user)
            send_notifications([user], 'group_admin_rights_granted',
              {'group': group})
            send_notifications(list(group.admins.all()), 'new_group_admin',
              {'new_admin': user, 'group': group})
    else:
        raise Http404("Ain't here!")
    return HttpResponse('ok')


@login_required
def discard_invitation(request, invitation_id):
    if not request.method == 'POST':
        raise Http404("Ain't here!")
    invitation = get_object_or_404(Invitation, pk=invitation_id)
    if not invitation.group.has_admin(request.user):
        raise PermissionError("You can't!")
    was_pending = invitation.accepted is not None
    invitation.delete()
    if was_pending:
        request.user.message_set.create(
          message=_('The invitation was cancelled.'))
    else:
        request.user.message_set.create(
          message=_('The invitation was discarded.'))
    return HttpResponse('ok')


@login_required
def answer_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, pk=invitation_id,
      sent_to=request.user)  # requires testing!
    form = None
    if request.method == 'POST':
        if invitation.accepted is not None:
            return HttpResponseRedirect('')
        form = AnwserInvitationForm(request.POST)
        if form.is_valid():
            if int(form.cleaned_data['decision']):
                invitation.group.users.add(request.user)
                invitation.accepted = True
                request.user.message_set.create(message=_('You are now '
                  'a member of the group %s.') % invitation.group.name)
                send_notifications(list(invitation.group.admins.all()),
                  'new_group_member', {'new_member': request.user,
                  'group': invitation.group})
            else:
                invitation.accepted = False
                request.user.message_set.create(
                  message=_('The invitation has been declined.'))
            invitation.response_date = datetime.datetime.now()
            invitation.save()
    elif invitation.accepted is None:
        form = AnwserInvitationForm()
    return render_to_response('snapboard/invitation',
      {'form': form, 'invitation': invitation},
      context_instance=RequestContext(request, processors=extra_processors))


@login_required
def xmppresourcify(request, resource=None, post_id=None):
    _log.debug("resourcify: user: %r" % request.user)
    post = _get_that_post(request, post_id)
    if not resource:
        resource = "#%d-%d" % (post.id, post.thread.id)
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
        return render_to_response('snapboard/xmpp_help/%s' % subject,
          None,
          context_instance=RequestContext(request,
            processors=extra_processors),
          xrargs={'pttype': 'st'})
    except TemplateDoesNotExist:
        raise Http404("No such help subject")


RPC_ACTION_MAP = {
  "gsticky": r_set_gsticky,
  "csticky": r_set_csticky,
  "close": r_set_close,
  "censor": r_set_censor,
  "removethread": r_removethread,
  "abuse": r_abusereport,
  "watch": r_watch_post,
  "geteditform": edit_post,
  "getreplyform": post_reply,
  "getrevisions": show_revisions,
  }
