import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q

_log = logging.getLogger('snapboard.managers')


# Obsolete (not used) by now.
class PostManager(models.Manager):
    def get_query_set(self):
        select = {}
        extra_abuse_count = """
            SELECT COUNT(*) FROM snapboard_abusereport
                WHERE snapboard_post.id = snapboard_abusereport.post_id
            """
        select['abuse'] = extra_abuse_count

        return super(PostManager, self).get_query_set().extra(
            select=select).order_by('odate')


class ThreadManager(models.Manager):
    def get_query_set(self):
        '''
        This generates a QuerySet containing Threads and additional data used
        in generating a web page with a listing of discussions.
        http://code.django.com/ qset allows the caller to specify an initial
        queryset to work with.  If this is not set, all Threads will be
        returned.
        '''
        # number of posts in thread
        # ? XXX: censored threads don't count toward the total, even though
        # they are visible (but not their contents).
        extra_post_count = """
            SELECT COUNT(*) FROM snapboard_post
                WHERE snapboard_post.thread_id = snapboard_thread.id
                  AND NOT snapboard_post.censor
            """
        # figure out who started the discussion
        ## -
        extra_starter = """
            SELECT username FROM auth_user
                WHERE auth_user.id = (SELECT user_id
                    FROM snapboard_post WHERE snapboard_post.thread_id = snapboard_thread.id
                    ORDER BY snapboard_post.date ASC
                    LIMIT 1)
            """
        ## -
        extra_last_poster = """
            SELECT username FROM auth_user
                WHERE auth_user.id = (SELECT user_id
                    FROM snapboard_post WHERE snapboard_post.thread_id = snapboard_thread.id
                    ORDER BY snapboard_post.date DESC
                    LIMIT 1)
            """
        ## For sorting, especially.
        extra_last_updated = """
          SELECT date FROM snapboard_post
          WHERE snapboard_post.thread_id = snapboard_thread.id
          ORDER BY date DESC LIMIT 1
          """
        ## Extra info.
        extra_last_update = """
          SELECT id FROM snapboard_post
          WHERE snapboard_post.thread_id = snapboard_thread.id
          ORDER BY snapboard_post.date DESC LIMIT 1
          """
        # ! Might be better to use 'depth=1' here.
        extra_start = """
          SELECT id FROM snapboard_post
          WHERE snapboard_post.thread_id = snapboard_thread.id
          ORDER BY snapboard_post.date ASC LIMIT 1
          """
        return super(ThreadManager, self).get_query_set().extra(
            select={
                'post_count': extra_post_count,
                #'last_updated': extra_last_updated,
                ## bug: http://code.djangoproject.com/ticket/2210
                ## the bug is that any extra columns must match their names
                ## TODO: sorting on boolean fields is undefined in SQL theory
                'date': extra_last_updated,
                'last_post': extra_last_update,
                'first_post': extra_start,
                # ... -
                'starter': extra_starter,
                'last_poster': extra_last_poster,
            },).order_by('-gsticky', '-date'
            ).select_related()

    def get_user_query_set(self, user):
        try:
            us = user.sb_usersettings
        except ObjectDoesNotExist:
            pass
        else:
            if us.frontpage_filters.count():
                return self.get_query_set().filter(
                    category__in=us.frontpage_filters.all())
        return self.get_query_set()

    def get_favorites(self, user):
        wl = user.sb_watchlist.all()
        return self.get_query_set().filter(pk__in=[x.thread_id for x in wl])

    def get_category(self, cat_id):
        return self.get_query_set().filter(category__name=cat_id)


class CategoryManager(models.Manager):
    def get_query_set(self):
        thread_count = """
            SELECT COUNT(*) FROM snapboard_thread
            WHERE snapboard_thread.category_id = snapboard_category.id
            """
        return super(CategoryManager, self).get_query_set().extra(
            select={'thread_count': thread_count})
                
# vim: ai ts=4 sts=4 et sw=4
