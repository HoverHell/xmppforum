from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.defaultfilters import striptags
from django.utils import simplejson
from django.utils.translation import ugettext as _

from snapboard.models import Post, WatchList, AbuseReport, PermissionError
from snapboard.templatetags.extras import render_filter


def _sanitize(text):
    return render_filter(striptags(text), "safe")


def rpc_preview(request):
    text = request.raw_post_data 
    return HttpResponse(simplejson.dumps({'preview': _sanitize(text)}),
            mimetype='application/javascript')


def rpc_lookup(request, queryset, field, limit=5):
    # XXX We should probably restrict member (or other) lookups to registered users
    obj_list = []
    lookup = { '%s__icontains' % field: request.GET['query'],}
    for obj in queryset.filter(**lookup)[:limit]:
                obj_list.append({"id": obj.id, "name": getattr(obj, field)}) 
    object = {"ResultSet": { "total": str(limit), "Result": obj_list } }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')


def _toggle_boolean_field(object, field):
    '''
    Switches the a boolean value and returns the new value.
    object should be a Django Model
    '''
    setattr(object, field, (not getattr(object, field)))
    object.save()
    return getattr(object, field)


def rpc_csticky(request, **kwargs):
    if not request.user.is_staff:
        raise PermissionDenied
    if _toggle_boolean_field(kwargs['thread'], 'csticky'):
        return {'link':_('unset csticky'), 'msg':_('This thread is sticky in its category.')}
    else:
        return {'link':_('set csticky'), 'msg':_('Removed thread from category sticky list')}


def rpc_gsticky(request, **kwargs):
    if not request.user.is_staff:
        raise PermissionDenied
    if _toggle_boolean_field(kwargs['thread'], 'gsticky'):
        return {'link':_('unset gsticky'), 'msg':_('This thread is now globally sticky.')}
    else:
        return {'link':_('set gsticky'), 'msg':_('Removed thread from global sticky list')}


def rpc_close(request, **kwargs):
    if not request.user.is_staff:
        raise PermissionDenied
    if _toggle_boolean_field(kwargs['thread'], 'closed'):
        return {'link':_('open thread'), 'msg':_('This discussion is now CLOSED.')}
    else:
        return {'link':_('close thread'), 'msg':_('This discussion is now OPEN.')}

def rpc_censor(request, **kwargs):
    if not request.user.is_staff:
        raise PermissionDenied
    if _toggle_boolean_field(kwargs['post'], 'censor'):
        return {'link':_('uncensor'), 'msg':_('This post is censored!')}
    else:
        return {'link':_('censor'), 'msg':_('This post is no longer censored.')}

def rpc_quote(request, **kwargs):
    post = Post.objects.select_related().get(id=kwargs['oid'])
    if not post.thread.category.can_read(request.user):
        raise PermissionError
    return {'text': post.text, 'author': unicode(post.user)}
