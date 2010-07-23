import logging
import datetime

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
from django.utils import simplejson
from django.utils.translation import ugettext as _

# XmppFace
import xmppbase
from xmppbase import XmppRequest, XmppResponse
from xmppbase import render_to_response, success_or_reverse_redirect
from xmppstuff import send_notifications
#from django.contrib.auth.decorators import login_required
from xmppbase import login_required

# Avatar form in UserSettings
from avatar.models import Avatar, avatar_file_path
from avatar.forms import PrimaryAvatarForm, UploadAvatarForm
from avatar.views import _get_avatars, _notification_updated

from snapboard.forms import *
from snapboard.models import *
from snapboard.models import AnonymousUser
from snapboard.rpc import *

_log = logging.getLogger('snapboard.views')


# USE_SNAPBOARD_LOGIN_FORM, USE_SNAPBOARD_SIGNIN should probably be removed
USE_SNAPBOARD_SIGNIN = getattr(settings, 'USE_SNAPBOARD_SIGNIN', False)
USE_SNAPBOARD_LOGIN_FORM = getattr(settings, 'USE_SNAPBOARD_LOGIN_FORM', False)
ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', 'Anonymous')

if ANONYMOUS_NAME:
    ANONYMOUS_USER = User.objects.get(username=ANONYMOUS_NAME)
    def anonymous_login_required(function=None):
        """
        Decorator to replace auth's AnonymousUser with an actual usable user for
        particular views. Sets user.realy_anonymous if replaced. Configurable by
        ANONYMOUS_NAME in the settings.
        """
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
    """
    Provides some default information for all templates.

    This should be added to the settings variable TEMPLATE_CONTEXT_PROCESSORS
    """
    return {
            'SNAP_MEDIA_PREFIX': SNAP_MEDIA_PREFIX,
            'SNAP_POST_FILTER': SNAP_POST_FILTER,
            'LOGIN_URL': settings.LOGIN_URL,
            'LOGOUT_URL': settings.LOGOUT_URL,
            }


def user_settings_context(request):
    return {'user_settings': request.user.get_user_settings()}

if USE_SNAPBOARD_LOGIN_FORM:
    from snapboard.forms import LoginForm
    def login_context(request):
        '''
        All content pages that have additional content for authenticated users but
        that are also publicly viewable should have a login form in the side panel.
        '''
        response_dict = {}
        if not request.user.is_authenticated() \
          or getattr(request.user, "really_anonymous", False):
            # Anonuser can login, too.
            response_dict.update({
                    'login_form': LoginForm(),
                    })

        return response_dict
    extra_processors = [user_settings_context, login_context]
else:
    extra_processors = [user_settings_context]

def rpc(request):
    '''
    Delegates simple rpc requests.
    '''
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
    
    if action == 'quote':
        try:
            return HttpResponse(simplejson.dumps(rpc_func(request, oid=int(request.POST['oid']))))
        except (KeyError, ValueError):
            return HttpResponseServerError("RPC: Failed to find/process requested post.")

    try:
        # oclass_str will be used as a keyword in a function call, so it must
        # be a string, not a unicode object (changed since Django went
        # unicode). Thanks to Peter Sheats for catching this.
        oclass_str =  str(request.POST['oclass'].lower())
        oclass = RPC_OBJECT_MAP[oclass_str]
    except KeyError:
        return HttpResponseServerError("RPC: Unknown requested object type")

    try:
        oid = int(request.POST['oid'])

        if action in RPC_AACTIONS:  # Just do it.
            # Also, where should be 404 and PermissionError handled? In JS?
            return rpc_func(request, oid, rpc=True)
        
        # Otherwise...
        forum_object = oclass.objects.get(pk=oid)

        response_dict.update(rpc_func(request, **{oclass_str:forum_object}))
        return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')

    except oclass.DoesNotExist:
        print "RPC handler: no such class."
        return HttpResponseServerError("RPC handler: no such object class.")
    except KeyError:
        print "RPC handler: KeyError."
        return HttpResponseServerError("RPC handler: KeyError, likely malformed POST.")

def r_getreturn(request, rpc, next, rpcdata, successtext, postid=None):
    '''
    Common function for RPCable views to easily return some appropriate
    data.
    '''
    if rpc:  # explicit request to return RPC-usable data
        # Can do conversion in rpc(), though.
        return HttpResponse(simplejson.dumps(rpcdata), mimetype='application/javascript')
    else:
        next = next or request.GET.get('next')
        if next:  # know where should return to.
            return HttpResponseRedirect(next)
        else:  # explicitly return 
            if postid:  # we have a post to return to.
                return success_or_reverse_redirect('snapboard_locate_post',
                  args=(postid,), req=request, msg=successtext)
            # Might supply some more data if we need to return somewhere
            # else?
            return HttpResponseServerError("RPC return: unknown return.")  # Nothing else to do here.

def r_watch_post(request, post_id, next=None, rpc=False):
    try:
        post = Post.objects.get(id=int(post_id))
    except Post.DoesNotExist:
        raise Http404, "No such post to watch"
    thr = post.thread
    if not thr.category.can_read(request.user):
        raise PermissionError, "You are not allowed to do that"
    try:
        # Check if user's already subscribed to that branch? (post__in get_ancestors)
        wl = WatchList.objects.get(user=request.user, post=post)
        # it exists, stop watching it
        wl.delete()
        return r_getreturn(request, rpc, next, {'link':_('watch'),
          'msg':_('This thread has been removed from your favorites.')},
          "Watch removed.", postid=post.id)
    except WatchList.DoesNotExist:
        # create it
        wl = WatchList(user=request.user, post=post)
        wl.save()
        return r_getreturn(request, rpc, next, {'link':_('dont watch'),
          'msg':_('This thread has been added to your favorites.')},
          "Watch added.", postid=post.id)


RPC_OBJECT_MAP = {
        "thread": Thread,
        "post": Post,
        }

RPC_ACTION_MAP = {
        "censor": rpc_censor,
        "gsticky": rpc_gsticky,
        "csticky": rpc_csticky,
        "close": rpc_close,
        "abuse": rpc_abuse,
        "watch": r_watch_post,
        "quote": rpc_quote,
        }
# Temporary list of RPC functions coverted to advanced action handers.
RPC_AACTIONS = ["watch"]


def thread(request, thread_id):
    try:
        thr = Thread.view_manager.get(pk=thread_id)
    except Thread.DoesNotExist:
        raise Http404, "Thread not found"

    if not thr.category.can_read(request.user):
        raise PermissionError, "You are not allowed to read this thread"

    render_dict = {}

    postform = PostForm()

    #if request.user.is_authenticated():
    #    render_dict.update({"watched": WatchList.objects.filter(user=request.user, thread=thr).count() != 0})

    # this must come after the post so new messages show up

    ## Revisions of root node become a serious special case.
    ## Not sure about right way, so this is more of a hack-in:
    # Get original tree root (really, better point to it in the Thread object!)
    top_post_0 = Post.objects.filter(thread=thread_id, depth=1)[0]
    # Get latest version of top post (to display it).
    top_post = Post.objects.get(thread=thread_id, depth=1, revision=None)
    # Get all replies.
    post_list = Post.get_children(top_post_0)  # Paginated by this list.
    
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
            'postform': postform,
            'thr': thr,
            })
    
    return render_to_response('snapboard/thread',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))
thread = anonymous_login_required(thread)


def post_reply(request, parent_id, thread_id=None):
    # thread_id paremeter was considered unnecessary here.
    # Although, '#thread_id/post_id_in_thread' might be preferrable to using
    # global post id.
    try:
        parent_post = Post.objects.get(id=int(parent_id))
    except Post.DoesNotExist:
        raise Http404, "Reply to WHAT?"
    if request.POST:  # POST HERE.
        thr = parent_post.thread
        if not thr.category.can_post(request.user):
            raise PermissionError, "You are not allowed to post in this thread"
        postform = PostForm(request.POST)
        if postform.is_valid():
            postobj = parent_post.add_child(thread = thr,
                    user = request.user,
                    text = postform.cleaned_data['post'],
                    )
            postobj.save() # this needs to happen before many-to-many private is assigned

            if len(postform.cleaned_data['private']) > 0:
                _log.debug('thread(): new post private = %s' % postform.cleaned_data['private'])
                postobj.private = postform.cleaned_data['private']
                postobj.is_private = True
                postobj.save()
            postobj.notify()
            return success_or_reverse_redirect('snapboard_locate_post',
              args=(postobj.id,), req=request, msg="Posted successfully.")
    else:
        postform = PostForm()
    return render_to_response('snapboard/post_reply',
            {'postform': postform,
            },
            context_instance=RequestContext(request, processors=extra_processors))
post_reply = anonymous_login_required(post_reply)


def edit_post(request, original, next=None):
    '''
    Edit an existing post.
    '''
    #if not request.method == 'POST':
    #    raise Http404, "It ain't here!"  # ! Not compatible with non-JS.

    try:
        orig_post = Post.objects.get(id=int(original), revision=None)
    except Post.DoesNotExist:
        raise Http404, "Edit WHAT?"
        
    if orig_post.user != request.user or not orig_post.thread.category.can_post(request.user):
        # ? Anonymous post editing? o-O
        # ! Not in sync with interface in thread!
        raise PermissionError, "You are not allowed to edit that."

    if request.POST:
        postform = PostForm(request.POST)
        if postform.is_valid():
            # create the post
            parent = orig_post.get_parent()
            postdata = {
                    "user": request.user,
                    "thread": orig_post.thread,
                    "text": postform.cleaned_data['post'],
                    "previous": orig_post,
            }
            if parent:
                post = parent.add_child(**postdata)
            else:
                post = Post.add_root(**postdata)
            post.save()
            post.private = orig_post.private.all()
            post.is_private = orig_post.is_private
            post.save()

            orig_post.revision = post
            orig_post.save()

            div_id_num = post.id
        else:
            div_id_num = orig_post.id

        next = request.GET.get('next')
        if next:  # shouldn't happen with XMPP.
            return HttpResponseRedirect(next.split('#')[0] + '#snap_post' + str(div_id_num))
        else:
            return success_or_reverse_redirect('snapboard_locate_post',
              args=(orig_post.id,), req=request, msg="Message updated.")
    else:  # Show a form for posting.
        return render_to_response('snapboard/edit_post',
                {'post': orig_post,
                },
                context_instance=RequestContext(request, processors=extra_processors))
edit_post = anonymous_login_required(edit_post)  # ! Anonymous post revisions! yay!


def show_revisions(request, post_id):
    '''
    See all revisions of a specific post (for non-JS browsing).
    '''
    try:
        orig_post = Post.objects.get(id=int(post_id))
    except Post.DoesNotExist:
        raise Http404, "Don't know such post!"

    # revision => newer
    # previous => older
    post = orig_post
    posts = [post]
    while post.previous:
        post = post.previous
        posts.append(post)
    post = orig_post
    posts = posts[::-1]  # reverse the array.
    while post.revision:
        post = post.revision
        posts.append(post)
    
    return render_to_response('snapboard/show_revisions',
            {'posts': posts,
             'last_post': posts[-1],
             'thread': posts[-1].thread,
            },
            context_instance=RequestContext(request, processors=extra_processors))


##
# Should new discussions be allowed to be private?  Leaning toward no.
def new_thread(request, cat_id):
    '''
    Start a new discussion.
    '''
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
new_thread = anonymous_login_required(new_thread)


def watchlist(request):
    '''
    This page shows the posts that have been marked as 'watched'
    by the user.
    '''
    post_list = filter(lambda p: p.thread.category.can_view(request.user),
      [w.post for w in WatchList.objects.select_related(depth=3).filter(user=request.user)])
    # Pagination? Looks nice to allow in-url parameter like "?ppp=100".

    return render_to_response('snapboard/watchlist',
            {'posts': post_list},
            context_instance=RequestContext(request, processors=extra_processors))
watchlist = login_required(watchlist)

def private_index(request):
    thread_list = [thr for thr in Thread.view_manager.get_private(request.user) if thr.category.can_read(request.user)]

    render_dict = {'title': _("Discussions with private messages to you"), 'threads': thread_list}

    return render_to_response('snapboard/thread_index',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))
private_index = login_required(private_index)

def category_thread_index(request, cat_id):
    try:
        cat = Category.objects.get(pk=cat_id)
        if not cat.can_read(request.user):
            raise PermissionError, "You cannot list this category"
        thread_list = Thread.view_manager.get_category(cat_id)
        render_dict = ({'title': ''.join((_("Category: "), cat.label)), 'category': cat, 'threads': thread_list})
    except Category.DoesNotExist:
        raise Http404, "Category not found."
    return render_to_response('snapboard/thread_index_categoryless',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))
category_thread_index = anonymous_login_required(category_thread_index)

def thread_index(request, num_limit=None, num_start=None):
    if request.user.is_authenticated():
        # filter on user prefs
        thread_list = Thread.view_manager.get_user_query_set(request.user)
    else:
        thread_list = Thread.view_manager.get_query_set()
    thread_list = filter(lambda t: t.category.can_view(request.user), thread_list)
    # ! This should be common with few more views, probably.
    if isinstance(request, XmppRequest):  # Apply Xmpp-specific limits
        # ? int() failure would mean programming error... or not?
        num_start=int(num_start or 1)-1 # Starting from humanized '1'.
        num_limit=int(num_limit or 20)
        thread_list=thread_list[num_start:num_start+num_limit]
    render_dict = {'title': _("Recent Discussions"), 'threads': thread_list}
    return render_to_response('snapboard/thread_index',
            render_dict,
            context_instance=RequestContext(request, processors=extra_processors))

def locate_post(request, post_id):
    '''
    Redirects to a post, given its ID.
    '''
    post = get_object_or_404(Post, pk=post_id)
    if not post.thread.category.can_read(request.user):
        raise PermissionError, "You cannot see it"
    if post.is_private and not (post.user==request.user or post.private.filter(pk=request.user.id).count()):
        raise PermissionError, "What?"
    # Count the number of visible posts before the one we are looking for, 
    # as well as the total
    #total = post.thread.count_posts(request.user)

    # ...everything is visible, threads paginated by first-leve answers.
    # Looks funny, meh.
    root=post.get_root()
    total = root.get_children_count()
    answer = post.get_ancestors()[1] if post.depth > 2 else post
    preceding_count = (i for i,x in enumerate(answer.get_siblings()) if x == answer).next()+1
    
    # Later TODO: correct for possible thread rollups - add ?unfold=threadnum or smth.
    
    #preceding_count = post.thread.count_posts(request.user, before=post.date)
    # Check the user's settings to locate the post in the various pages
    settings = request.user.get_user_settings()
    ppp = settings.ppp
    if total < ppp:
        page = 1
    elif settings.reverse_posts:
        page = (total - preceding_count - 1) // ppp + 1
    else:
        page = preceding_count // ppp + 1
    return HttpResponseRedirect('%s?page=%i#snap_post%i' % (reverse('snapboard_thread', args=(post.thread.id,)), page, post.id))

def category_index(request):
    return render_to_response('snapboard/category_index',
            {
            'cat_list': [c for c in Category.objects.all() if c.can_view(request.user)],
            },
            context_instance=RequestContext(request, processors=extra_processors))

def edit_settings(request):
    '''
    Allow user to edit his/her profile. Requires login.

    There are 4 buttons on this page: choose avatar, delete avatar, upload
    avatar, change settings.
    '''
    userdata, userdatacreated = UserSettings.objects.get_or_create(user=request.user)
    avatar, avatars = _get_avatars(request.user)
    if avatar:
        kwargs = {'initial': {'choice': avatar.id}}
    else:
        kwargs = {}
    settings_form, primary_avatar_form, upload_avatar_form = None, None, None
    # ! Actually, the avatars code was mostly copied from avatar/views.py
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
edit_settings = login_required(edit_settings)

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
manage_group = login_required(manage_group)

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
invite_user_to_group = login_required(invite_user_to_group)

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
remove_user_from_group = login_required(remove_user_from_group)

def grant_group_admin_rights(request, group_id):
    '''
    Although the Group model allows non-members to be admins, this view won't 
    let it.
    '''
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
grant_group_admin_rights = login_required(grant_group_admin_rights)

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
discard_invitation = login_required(discard_invitation)

def answer_invitation(request, invitation_id):
    invitation = get_object_or_404(Invitation, pk=invitation_id)
    if request.user != invitation.sent_to:  # ! Probably should be included into above.
        raise Http404, "No Invitation matches the given query."
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
answer_invitation = login_required(answer_invitation)


def xmpp_get_help(request, subject=None):
    '''
    Returns help message to the user, possibly on the specific subject.

    Can theoretically be used in the web view as well.
    '''
    subject = subject or "main"
    try:
        return render_to_response('snapboard/xmpp_help/%s'%subject, 
          None,
          context_instance=RequestContext(request,
            processors=extra_processors))
    except TemplateDoesNotExist:
        raise Http404, "No such help subject"

def xmpp_register_cmd(request, nickname=None, password=None):
    '''
    Provides all necessart registration-related functionality for XMPP.

    XMPP-only view.
    '''
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
            else:
                rusersettings.jid = request.srcjid  # replace its JID
                rusersettings.save()
                return XmppResponse(_("JID setting updated successfully."))
        else:
            raise PermissionError, "Authentication to existing user failed"
    # Optional: change state to 'password input' if no password
    # !! Possible problem if password (or, esp., both) contain spaces.


def _brand_view(func):
    '''
    Mark a view as belonging to SNAPboard.

    Allows the UserBanMiddleware to limit the ban to SNAPboard in larger 
    projects.
    '''
    setattr(func, '_snapboard', True)


_brand_view(rpc)
_brand_view(thread)
_brand_view(edit_post)
_brand_view(new_thread)
_brand_view(watchlist)
_brand_view(private_index)
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
