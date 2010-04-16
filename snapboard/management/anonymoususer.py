import os

from django.db.models import signals 
from django.conf import settings

from snapboard import models as snapboard_app

# Creates an anonymous user needed for appropriate functioning of the app
# (if configured so, at least)
def add_anonymous(**kwargs):
    ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', 'Anonymous')

    if ANONYMOUS_NAME:  # It is set. Create one.
        print("Creating anonymous user named \"%s\":" % ANONYMOUS_NAME)
        from snapboard.models import Group, User
        anonuser = User.objects.create_user(ANONYMOUS_NAME, "", None)
        print("  ...done.")
        
signals.post_syncdb.connect(add_anonymous, sender=snapboard_app) 
