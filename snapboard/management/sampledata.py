""" Offers to generate sample data on the initial syncdb.  """

from django.db.models import signals
from django.conf import settings

from snapboard import models as snapboard_app


def test_setup(**kwargs):
    from snapboard.models import Thread

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

    from  snapboard.management.commands.gen_data_def import _gen_data_def
    from snapboard.management.commands.gen_threads_def import _gen_threads_def
    _gen_data_def()
    _gen_threads_def()

signals.post_syncdb.connect(test_setup, sender=snapboard_app)
