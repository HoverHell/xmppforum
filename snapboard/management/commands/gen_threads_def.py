""" A simple hack-up for generating random threads for testing.  """

from django.core.management.base import NoArgsCommand

from random import choice, randrange

from snapboard.models import Thread, Category
from snapboard import sampledata
from snapboard.management.commands.gen_threads import make_random_post_tree

def _gen_threads_def():
    thtypes = (
      ("[wide]", 0.1),
      ("[e]", 0.5),
      ("[deep]", 0.98),
    )
    for i in xrange(3):
        cat = choice(Category.objects.all())
        subj = choice(sampledata.objects.split('\n')) + \
          " " + thtypes[i][0]
        thread = Thread(subject=subj, category=cat)
        thread.save()
        print 'thread ', i, 'created'
        make_random_post_tree(None, randrange(50, 100), thread,
          ratio=thtypes[i][1])
        print 'thread ', i, 'filled'


class Command(NoArgsCommand):
    help = 'Generate a default set of sample threads.'

    def handle_noargs(self, *args, **kwargs):
        _gen_threads_def()
