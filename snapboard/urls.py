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

from django.views.decorators.cache import cache_page
from django.views.generic.simple import direct_to_template


# post_id_re = '[#!][0-9A-Fa-f]+/[0-9A-Fa-f]+'
from snapboard.models import Post
post_id_re = Post.id_m_re_f
# dual id regex.
post_id_re_d = r'((?P<post_id>\d+)|(?P<post_form_id>' + post_id_re + r'))'

feeds = {'latest': LatestPosts}


js_info_dict = {
    'packages': ('snapboard',),
}


urlpatterns = patterns('',
    (r'^$', merged_index, {}, 'snapboard_index'),

    ## Main indexes.
    (r'^t/(?P<thread_id>\d+)/$', thread, {}, 'snapboard_thread'),
    (r'^p/' + post_id_re_d + r'/$',
      thread_post, {}, 'snapboard_thread_post'),
    # TODO: thread_latest (+rss?)
    (r'^ti/$', thread_index, {}, 'snapboard_thread_index'),
    (r'^ci/$', category_index, {}, 'snapboard_category_index'),
    (r'^c/(?P<cat_id>\d+)/$',
      category_thread_index, {}, 'snapboard_category_thread_index'),

    (r'^tn/(?:(?P<cat_id>\d+)/)?$',
      new_thread, {}, 'snapboard_new_thread'),
    (r'^settings/$', edit_settings, {}, 'snapboard_edit_settings'),

    (r'^r/' + post_id_re_d + r'/$',
      post_reply, {}, 'snapboard_post_reply'),
    (r'^e/' + post_id_re_d + r'/$',
      edit_post, {}, 'snapboard_edit_post'),
    (r'^rv/' + post_id_re_d + r'/$',
      show_revisions, {}, 'snapboard_show_revisions'),
    (r'^watchlist/$', watchlist, {}, 'snapboard_watchlist'),
    ## RPCable views.
    (r'^w/' + post_id_re_d + r'/$',
      r_watch_post, {}, 'snapboard_watch_post'),
    (r'^r_removethread/(?P<thread_id>\d+)/$',
      r_removethread, {}, 'snapboard_remove_thread'),
    # ... togglers.
    # ? XXX: auto-generate from list?
    (r'^r_set_gsticky/(?P<oid>\d+)/(?: (?P<state>1|0))?$',
      r_set_gsticky, {}, 'snapboard_set_gsticky'),
    (r'^r_set_csticky/(?P<oid>\d+)/(?: (?P<state>1|0))?$',
      r_set_csticky, {}, 'snapboard_set_csticky'),
    (r'^r_set_close/(?P<oid>\d+)/(?: (?P<state>1|0))?$',
      r_set_close, {}, 'snapboard_set_close'),
    (r'^scen/(?P<oid>\d+)/(?: (?P<state>1|0))?$',
      r_set_censor, {}, 'snapboard_set_censor'),

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
    (r'^rpc/action/$', rpc_dispatch, {}, 'snapboard_rpc_action'),
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

    (r'^mv/volatile.css',
      cache_page(direct_to_template, 3600 * 24 * 7),
      {'template': 'snapboard/volatile.css'},
      'snapboard_vcss'),
)
