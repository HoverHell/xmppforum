from snapboard.views import *
from snapboard.models import *

from optparse import make_option
from django.core.management.base import BaseCommand

import random
import traceback

def _make_testtrees(maxdepth=512):
    thr = Thread(subject="Test trees.", category=Category.objects.all()[0])
    thr.save()
    top_post = Post.add_root(user=user, thread=thr, text="subj.")
    try:
        post = top_post
        print "lin"
        for d in xrange(2, max):
            post = post.add_child(text="#1 at %d (lin)" % d, user=post.user, thread=post.thread)
            print d
    except Exception:
        traceback.print_exc()

    try:
        post = top_post
        print "dbl"
        for d in xrange(2, max):
            post1 = post.add_child(text="#1 at %d (dbl)" % d, user=post.user, thread=post.thread)
            post2 = post.add_child(text="#2 at %d (dbl)" % d, user=post.user, thread=post.thread)
            post = post1
            print d
    except Exception:
        traceback.print_exc()

    try:
        post = top_post
        print "rnd"
        for d in xrange(2, max):
            post1 = post.add_child(text="#1 at %d (rnd)" % d, user=post.user, thread=post.thread)
            post2 = post.add_child(text="#2 at %d (rnd)" % d, user=post.user, thread=post.thread)
            post1.save()
            post2.save()
            post = post1 if random.choice([True, False]) else post2
            print d
    except Exception:
        traceback.print_exc()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-d', default=255, dest='maxdepth', type='int',
            help='maximal depth to generate (if allowed by db)'),
    )

    help = 'Generate some testing trees.'

    def handle(self, *args, **kwargs):
        make_random_threads(**kwargs)
