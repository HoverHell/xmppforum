from django.conf.urls.defaults import *

from views import thread, thread_index, new_thread, category_index
from views import edit_post, rpc, signout, signin
from views import favorite_index

from rpc import rpc_post
from feeds import LatestPosts

feeds = {
    'latest': LatestPosts,
    }


urlpatterns = patterns('',
    (r'^$', thread_index),
    (r'^signout/$', signout),
    (r'^signin/$', signin),
    (r'^newtopic/$', new_thread),
    (r'^categories/$', category_index),
    (r'^favorites/$', favorite_index),
    (r'^edit_post/(?P<original>\d+)/$', edit_post),
    (r'^threads/$', thread_index),
    (r'^threads/page(?P<page>\d+)/$', thread_index),
    (r'^threads/id/(?P<thread_id>\d+)/$', thread),
    (r'^threads/id/(?P<thread_id>\d+)/page(?P<page>\d+)/$', thread),
    (r'^threads/category/(?P<cat_id>\d+)/$', thread_index),
    (r'^threads/category/(?P<cat_id>\d+)/page(?P<page>\d+)/$', thread_index),

    # RPC
    (r'^rpc/action/$', rpc),
    (r'^rpc/postrev/$', rpc_post),

    # feeds
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
)
