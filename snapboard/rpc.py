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
    obj_list = []
    lookup = { '%s__icontains' % field: request.GET['query'],}
    for obj in queryset.filter(**lookup)[:limit]:
                obj_list.append({"id": obj.id, "name": getattr(obj, field)}) 
    object = {"ResultSet": { "total": str(limit), "Result": obj_list } }
    return HttpResponse(simplejson.dumps(object), mimetype='application/javascript')
