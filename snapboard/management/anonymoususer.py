""" Creates an anonymous user needed for appropriate functioning of the app
(if configured so, at least). """

import os

from django.db.models import signals 
from django.conf import settings

from snapboard import models as snapboard_app

def add_anonymous(**kwargs):
    ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', 'Anonymous')

    if ANONYMOUS_NAME:  # It is set. Create one if there's none.
        from snapboard.models import User
        if User.objects.filter(username=ANONYMOUS_NAME):
            # It exists already.
            return
        print("Creating anonymous user named \"%s\":" % ANONYMOUS_NAME)
        anonuser = User.objects.create_user(ANONYMOUS_NAME, "", None)
        print("  ...done.")
        
signals.post_syncdb.connect(add_anonymous, sender=snapboard_app) 
