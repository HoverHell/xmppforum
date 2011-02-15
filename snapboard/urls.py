""" url patterns for xmppforum-snapboard, usually included as part of
xmppforum """

# pylint: disable=C0103,W0401,W0614
# 'urlpatterns' is forced, and importing * is more clean visually.

from django.contrib.auth.models import User

from snapboard.feeds import LatestPosts
from snapboard.rpc import rpc_lookup, rpc_preview
from snapboard.views import *

from django.conf.urls.defaults import patterns
#from django.conf.urls.defaults import handler404, handler500, include

feeds = {'latest': LatestPosts}

js_info_dict = {
    'packages': ('snapboard',),
}

urlpatterns = patterns('',
    (r'^$', thread_index, {}, 'snapboard_index'),
    (r'^categories/$', category_index, {}, 'snapboard_category_index'),
    (r'^watchlist/$', watchlist, {}, 'snapboard_watchlist'),
    # Please note that next two have to end with post id (required for
    #  javascript features)
    (r'^post_reply/(?P<parent_id>\d+)/$',
         post_reply, {}, 'snapboard_post_reply'),
    (r'^edit_post/(?P<original>\d+)/$',
         edit_post, {}, 'snapboard_edit_post'),
    (r'^show_revisions/(?P<post_id>\d+)/$',
         show_revisions, {}, 'snapboard_show_revisions'),
    # RPCale views.
    (r'^r_watch_post/(?P<post_id>\d+)/$',
         r_watch_post, {}, 'snapboard_watch_post'),
    (r'^r_removethread/(?P<thread_id>\d+)/$',
         r_removethread, {}, 'snapboard_remove_thread'),
    (r'^threads/$', thread_index, {}, 'snapboard_thread_index'),
    (r'^threads/id/(?P<thread_id>\d+)/$', thread, {}, 'snapboard_thread'),
    (r'^threads/category/(?P<cat_id>\d+)/$',
         category_thread_index, {}, 'snapboard_category_thread_index'),
    (r'^threads/category/(?P<cat_id>\d+)/newtopic/$',
         new_thread, {}, 'snapboard_new_thread'),
    (r'^threads/post/(?P<post_id>\d+)/$',
         locate_post, {}, 'snapboard_locate_post'),
    (r'^settings/$', edit_settings, {}, 'snapboard_edit_settings'),

    ## Groups
    (r'^groups/(?P<group_id>\d+)/manage/$',
         manage_group, {}, 'snapboard_manage_group'),
    (r'^groups/(?P<group_id>\d+)/invite/$',
         invite_user_to_group, {}, 'snapboard_invite_user_to_group'),
    (r'^groups/(?P<group_id>\d+)/remuser/$',
         remove_user_from_group, {}, 'snapboard_remove_user_from_group'),
    (r'^groups/(?P<group_id>\d+)/grant_admin/$',
         grant_group_admin_rights, {},
        'snapboard_grant_group_admin_rights'),

    ## Invitations
    (r'invitations/(?P<invitation_id>\d+)/discard/$',
         discard_invitation, {}, 'snapboard_discard_invitation'),
    (r'invitations/(?P<invitation_id>\d+)/answer/$',
         answer_invitation, {}, 'snapboard_answer_invitation'),

    ## RPC
    (r'^rpc/action/$', rpc, {}, 'snapboard_rpc_action'),
    (r'^rpc/preview/$', rpc_preview, {}, 'snapboard_rpc_preview'),
    (r'^rpc/user_lookup/$', rpc_lookup,
        {
         'queryset': User.objects.all(),
         'field': 'username',
        }, 'snapboard_rpc_user_lookup'),

    ## feeds
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
        {'feed_dict': feeds}, 'snapboard_feeds'),

    ## javascript translations
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog',
        js_info_dict, 'snapboard_js_i18n'),
)
