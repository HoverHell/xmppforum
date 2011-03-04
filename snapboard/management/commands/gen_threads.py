""" A simple hack-up for generating random threads for testing.  """

from optparse import make_option
from django.core.management.base import BaseCommand

from django.db.models import signals 
from django.conf import settings

from snapboard import models as snapboard_app

from random import choice, randrange
from django.contrib.auth.models import User
from snapboard.models import Thread, Post, Category
from snapboard import sampledata

def make_random_post_tree(parent_post, amount, thread, ratio=0.5, **kwargs):
    text = '\n\n'.join([sampledata.sample_data() for x in range(0, choice(range(2, 5)))])
    # the post data
    postdata = {
      "user": choice(User.objects.all()),
      "thread": thread,
      "text": text,
      "ip": '.'.join([str(choice(range(2,254))) for x in xrange(4)]),
    }
    # Create a post in tree.
    if parent_post is None:  # Root node.
        post = Post.add_root(**postdata)
    else:
        post = parent_post.add_child(**postdata)
    # allows setting of arbitrary ip
    post.management_save()
    posts_remain = amount - 1  # Minus just-created one
    
    # ... got better ideas?
    # (got non-uniform random distributions?)
    # Anyway, ratio ~= depth/width. Don't delegate too few / too much to
    # each child depending on the ratio.
    fmin = lambda ratio, posts_remain: int(posts_remain * (ratio - 0.5)
      * 2) + 1 if ratio > 0.5 else 1
    fmax = lambda ratio, posts_remain: int(posts_remain * ratio * 2) + 2 \
      if ratio < 0.5 else posts_remain + 1

    while posts_remain > 0:  # Distribute remnants
        next_tree_posts = randrange(fmin(ratio, posts_remain),
          fmax(ratio, posts_remain))
        #print(" D: delegating %d,   %d remain " % (xx, x-xx))
        make_random_post_tree(post, next_tree_posts, thread)
        posts_remain -= next_tree_posts

def make_random_thread(nposts=100, cat=None, ratio=0.5):
    cat = Category.objects.get(pk=cat) if cat else choice(Category.objects.all())
    subj = choice(sampledata.objects.split('\n'))
    thread = Thread(subject=subj, category=cat)
    thread.save()
    n = randrange(nposts//2, nposts)  # Amount of posts in whole tread tree
    make_random_post_tree(None, n, thread, ratio=ratio)

def make_random_threads(nthreads, nposts=19, cat=None, ratio=0.5):
    for i in range(nthreads):
        make_random_thread(nposts, cat, ratio)
        print 'thread ', i, 'created'


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-n', default=10, dest='nthreads', type='int',
            help='amount of threads to generate'),
        make_option('-p', default=10, dest='nposts', type='int',
            help='approximate amount of posts to generate'),
        make_option('-c', default=None, dest='cat', type='int',
            help='category (id) to put them into (default: random)'),
        make_option('-r', default=None, dest='ratio', type='int',
            help='approximate width/depth ratio of the generated post tree.'),
    )

    help = 'Generate some random threads.'

    def handle(self, *args, **kwargs):
        make_random_threads(**kwargs)
