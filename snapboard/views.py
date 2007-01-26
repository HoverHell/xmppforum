from django.core.paginator import ObjectPaginator, InvalidPage
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseServerError
#from django.template import Context, loader
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import simplejson

from models import Thread, Post, Category, WatchList
from forms import PostForm, ThreadForm
from rpc import *


RPC_OBJECT_MAP = {
        "thread": Thread,
        "post": Post,
        }

RPC_ACTION_MAP = {
        "censor": rpc_censor,
        "gsticky": rpc_gsticky,
        "csticky": rpc_csticky,
        "abuse": rpc_abuse,
        "watch": rpc_watch,
        }


# Create your views here.
def rpc(request):
    if not request.POST or not request.user.is_authenticated():
        return HttpResponseServerError

    response_dict = {}

    try:
        oclass_str =  request.POST['oclass'].lower()
        oclass = RPC_OBJECT_MAP[oclass_str]
    except KeyError:
        return HttpResponseServerError

    try:
        oid = int(request.POST['oid'])
        action = request.POST['action'].lower()

        forum_object = oclass.objects.get(pk=oid)

        rpc_func = RPC_ACTION_MAP[action]

        response_dict.update(rpc_func(request, **{oclass_str:forum_object}))
        return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')

    except oclass.DoesNotExist:
        return HttpResponseServerError
    except KeyError:
        return HttpResponseServerError
    except AssertionError:
        return HttpResponseServerError



def thread(request, thread_id, page=1):
    # split results into pages
    ppp = 20                # P(osts) P(er) P(age)
    page = int(page)        # indexed starting at 1
    pindex = page - 1       # indexed starting at 0

    try:
        thr = Thread.objects.get(pk=thread_id)
        post_list = Post.objects.filter(thread=thr).order_by('-date').exclude(
                revision__isnull=False)

        paginator = ObjectPaginator(post_list, ppp)
        post_page = paginator.get_page(pindex)
    except Thread.DoesNotExist:
        raise Http404
    except InvalidPage:
        raise Http404

    render_dict = {}

    try:
        wl = WatchList.objects.get(user=request.user, thread=thr)
        render_dict.update({"watched":True})
    except WatchList.DoesNotExist:
        render_dict.update({"watched":False})

    if request.user.is_authenticated() and request.POST:
        postform = PostForm(request.POST.copy())


        if postform.is_valid():
            # reset post object
            postobj = Post(thread = thr,
                    user = request.user,
                    text = postform.clean_data['post'],
                    ip = request.META.get('REMOTE_ADDR', ''))
            postobj.save()
            postform = PostForm()
    else:
        postform = PostForm()

    # general info to render the page navigation (back/forward/etc)
    render_dict.update(paginate_render_dict(paginator, page))

    render_dict.update({
            'thr': thr,
            'postform': postform,
            'post_page': post_page,
            })

    return render_to_response('snapboard/thread.html',
            render_dict,
            context_instance = RequestContext(request))


def paginate_render_dict(paginator, page):
    pindex = page - 1
    page_next = None
    page_prev = None
    page_range = None
    if paginator.has_next_page(pindex):
        page_next = page + 1
    if paginator.has_previous_page(pindex):
        page_prev = page - 1
    if paginator.pages > 2:
        page_range = range(1, paginator.pages+1)

    return {
            'page': page,
            'page_total': paginator.pages,
            'page_next': page_next,
            'page_prev': page_prev,
            'page_range': page_range,
        }


def edit_post(request, original):
    '''
    Edit an original post.
    '''
    if not request.user.is_authenticated() or not request.POST:
        raise Http404

    try:
        orig_post = Post.objects.get(pk=int(original))
    except Post.DoesNotExist:
        raise Http404

    postform = PostForm(request.POST.copy())
    if postform.is_valid():
        # create the post
        post = Post(
                user = request.user,
                thread = orig_post.thread,
                text = postform.clean_data['post'],
                ip = request.META.get('REMOTE_ADDR', ''),
                previous = orig_post,
                )
        post.save()

        orig_post.revision = post
        orig_post.save()

        return HttpResponseRedirect('/snapboard/threads/id/'
                + str(orig_post.thread.id) + '/')
    else:
        return HttpResponseRedirect('/snapboard/threads/id/'
                + str(orig_post.thread.id) + '/')



def new_thread(request):
    if request.user.is_authenticated() and request.POST:
        threadform= ThreadForm(request.POST.copy())
        if threadform.is_valid():
            # create the thread
            thread = Thread(
                    subject = threadform.clean_data['subject'],
                    category = Category.objects.get(pk=
                        threadform.clean_data['category']),
                    )
            thread.save()

            # create the post
            post = Post(
                    user = request.user,
                    thread = thread,
                    text = threadform.clean_data['post'],
                    ip = request.META.get('REMOTE_ADDR', ''),
                    )
            post.save()

            # redirect to new thread
            return HttpResponseRedirect('/snapboard/threads/id/' + str(thread.id) + '/')
    else:
        threadform = ThreadForm()

    return render_to_response('snapboard/newthread.html',
            {
            'form': threadform,
            },
            context_instance = RequestContext(request))


def thread_index(request, cat_id=None, page=1):
    tpp = 20                # (T)threads (P)er (P)age
    page = int(page)
    pindex = page - 1

    try:
        if cat_id is None:
            thread_list = Thread.objects.all()
            page_title = "Recent Discussions"
        else:
            cat = Category.objects.get(pk=cat_id)
            thread_list = Thread.objects.filter(category=cat)
            page_title = ''.join(("Category: ", cat.label))

    except Category.DoesNotExist:
        raise Http404

    # number of posts in thread
    extra_post_count = """
        SELECT COUNT(*) FROM snapboard_post
            WHERE snapboard_post.thread_id = snapboard_thread.id
            AND snapboard_post.revision_id IS NULL
        """
    # figure out who started the population
    extra_starter = """
        SELECT username FROM auth_user
            WHERE auth_user.id = (SELECT user_id
                FROM snapboard_post WHERE snapboard_post.thread_id = snapboard_thread.id
                ORDER BY snapboard_post.date ASC
                LIMIT 1)
        """
    extra_last_poster = """
        SELECT username FROM auth_user
            WHERE auth_user.id = (SELECT user_id
                FROM snapboard_post WHERE snapboard_post.thread_id = snapboard_thread.id
                ORDER BY snapboard_post.date DESC
                LIMIT 1)
        """
    extra_last_updated = """
        SELECT date FROM snapboard_post 
            WHERE snapboard_post.thread_id = snapboard_thread.id
            ORDER BY date DESC LIMIT 1
        """

    thread_list = thread_list.extra(
        select = {
            'post_count': extra_post_count,
            'starter': extra_starter,
            #'last_updated': extra_last_updated,  # bug: http://code.djangoproject.com/ticket/2210
            'date': extra_last_updated,
            'last_poster': extra_last_poster,
        },).order_by('-gsticky', '-date')

    if cat_id:
        thread_list = thread_list.order_by('-csticky', '-date')

    # the bug is that any extra columns must match their names
    # TODO: sorting on boolean fields is undefined in SQL theory


    render_dict = {}

    try:
        paginator = ObjectPaginator(thread_list, tpp)
        thread_page = paginator.get_page(pindex)
        render_dict.update(paginate_render_dict(paginator, page))
    except InvalidPage:
        raise Http404

    render_dict.update({
            'thread_page': thread_page,
            'page_title': page_title,
            'category': cat_id,
            })

    return render_to_response('snapboard/thread_index.html',
            render_dict,
            context_instance = RequestContext(request))

def category_index(request):

    extra_post_count = """
        SELECT COUNT(*) FROM snapboard_thread
            WHERE snapboard_thread.category_id = snapboard_category.id
        """
    cat_list = Category.objects.all().extra(
        select = {'thread_count': extra_post_count},)

    return render_to_response('snapboard/category_index.html',
            {
            'cat_list': cat_list,
            },
            context_instance = RequestContext(request))
