""" Creates an anonymous user needed for appropriate functioning of the app
(if configured so, at least). """

import os

from django.db.models import signals 
from django.conf import settings
from django.contrib.auth import models as auth_app

def add_anonymous(**kwargs):
    ANONYMOUS_NAME = getattr(settings, 'ANONYMOUS_NAME', 'Anonymous')
    
    if ANONYMOUS_NAME:  # It is set. Create one if there's none.
        if auth_app.User.objects.filter(username=ANONYMOUS_NAME):
            # It exists already.
            return
        print "Creating anonymous user named \"%s\":" % ANONYMOUS_NAME
        anonuser = auth_app.User.objects.create_user(
          username=ANONYMOUS_NAME,
          email="", password=None)
        print "  ...done."

signals.post_syncdb.connect(add_anonymous, sender=auth_app) 
