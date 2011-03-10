""" A simple hack-up for generating random threads for testing.  """

from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User
from snapboard.models import Category


def _gen_data_def():
    # create some random users
    users = ('john', 'sally', 'susan', 'amanda', 'bob', 'tully', 'fran')
    for username in users:
        user = User.objects.get_or_create(username=username)
        # user.is_staff = True

    cats = (
      'Random Topics',
      'Bad Ideas',
      'Looking Around Dubious Stuff',
      'Unscientific Pondering. the',
    )
    for catlabel in cats:
        cat = Category.objects.get_or_create(label=catlabel)


class Command(NoArgsCommand):
    help = 'Generate some random threads.'

    def handle_noargs(self, *args, **kwargs):
        _gen_data_def()
