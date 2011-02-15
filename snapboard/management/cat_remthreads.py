""" Creates a special category for removed (hidden, censored) threads.
Configurable.  """

import os

from django.db.models import signals 
from django.conf import settings

from snapboard import models as snapboard_app

def add_remcat(**kwargs):
    CATNAME = getattr(settings, 'CAT_REMTHREADS_NAME',
      'Removed Threads')
    
    if not CATNAME:
        # Okay, not our problem. Die sometime later.
        return

    Category = snapboard_app.Category
    perm_nobody = snapboard_app.NOBODY
    if Category.objects.filter(label=CATNAME).exists():
        return  # It exists already.

    print "Creating the category of removed threads \"%s\":" % CATNAME
    #perms = [f.name for f in Category._meta.fields if f.name.endswith('_perms')]
    perms = ['view_perms', 'read_perms', 'post_perms', 'new_thread_perms']
    remcat = Category(label=CATNAME,
      **dict(zip(perms, [perm_nobody]*len(perms) ))
      )
    remcat.save()
    print "  ...done."

signals.post_syncdb.connect(add_remcat, sender=snapboard_app) 
