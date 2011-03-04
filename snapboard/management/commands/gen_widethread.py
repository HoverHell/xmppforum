from snapboard.views import *
from snapboard.models import *

from optparse import make_option
from django.core.management.base import BaseCommand

def _make_widethread(n=512, nlines=11):
    user = User.objects.all()[0]
    r = ['.'*i for i in range(1, (nlines+1)//2+1)]; r += r[::-1][1:]
    textbase = '\n'.join(r)
    thr = Thread(subject="WIDE.", category=Category.objects.all()[0])
    thr.save()
    top_post = Post.add_root(user=user, thread=thr, text="subj.")
    for i in range(n):
        top_post.add_child(user=user, thread=thr,
          text="post %s%d" % (textbase, i)).save()


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-n', default=512, dest='nthreads', type='int',
            help='amount of posts to make'),
        make_option('-l', default=10, dest='nlines', type='int',
            help='approximate amount of lines per post'),
    )

    help = 'Generate a wide test thread.'

    def handle(self, *args, **kwargs):
        _make_widethread(**kwargs)
