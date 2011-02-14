import os

from django.db.models import signals 
from django.conf import settings

from snapboard import models as snapboard_app

def test_setup(**kwargs):
    from random import choice, randrange
    from django.contrib.auth.models import User
    from snapboard.models import Thread, Post, Category
    from snapboard import sampledata


    if not settings.DEBUG:
        return

    if Thread.objects.all().count() > 0:
        # return if there seem to already be threads in the database.
        return
    
    populate = False
    if getattr(settings, 'M_AUTO_SAMPLEDATA', False):
        populate = "yes"
    
    msg = """
    You've installed SNAPboard with DEBUG=True, do you want to populate
    the board with random users/threads/posts to test-drive the application?
    (yes/no):
    """  # indent is printed.

    if not populate and kwargs.get('interactive', True):
        # ask for permission to create the test
        populate = raw_input(msg).strip()
        while not (populate == "yes" or populate == "no"):
            populate = raw_input("\nPlease type 'yes' or 'no': ").strip()
    
    if populate == "no" or populate == False:
        return

    # create some random users
    users = ('john', 'sally', 'susan', 'amanda', 'bob', 'tully', 'fran')
    for u in users:
        user = User.objects.get_or_create(username=u)
        # user.is_staff = True

    cats = (
      'Random Topics',
      'Bad Ideas',
      'Looking Around Dubious Stuff',
      'Unscientific Pondering. the',
    )

    for c in cats:
        cat = Category.objects.get_or_create(label=c)

    def make_random_post_tree(parent_post, amount, thread, ratio=0.5):
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

    # create up to 100 posts
    tc = range(1, 100)
    for i in xrange(3):
        cat = choice(Category.objects.all())
        subj = choice(sampledata.objects.split('\n')) + \
          " " + ["[wide]", "[e]", "[deep]"][i]
        thread = Thread(subject=subj, category=cat)
        thread.save()
        print 'thread ', i, 'created'
        
        n = choice(tc)  # Amount of posts in whole tread tree
        make_random_post_tree(None, n, thread, ratio=[0.1, 0.5, 0.98][i])

signals.post_syncdb.connect(test_setup, sender=snapboard_app) 
