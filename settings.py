# -*- coding: utf-8 -*-
# Django settings for examplesite project.

# Debug mode.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

LOGGING_INITIATED = False
# logging setup (copy to settings_local and change there, if needed)
import logging
def init_logging():
    logging.basicConfig(level=logging.INFO,
      #format='%(asctime)s %(name)s [%(levelname)s]: %(message)s',
      )

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

### django-defaultsite:
### Define an initial "base address" (set on first syncdb).
### Used in web-links in e-mail and XMPP messages.
### Can be changed later in admin interface in "Sites" category.
## The domain to use to replace 'example.com'. Defaults to your machine's hostname.
#SITE_DOMAIN = 'example.com'
## The site's name. Defaults to 'defaultsite' otherwise.
SITE_NAME = 'xmppforum'


# -------   -------   -------   Addresses and stuff. Almost certainly have to be changed.

DEFAULT_FROM_EMAIL = "jfu@localhost"



# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
# Full URI required for XMPP images to have any chances of working.
#MEDIA_URL = 'http://localhost:8000/media/'
MEDIA_URL = '/media/'


# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
# `pwgen -sy 50 1`, yet beware of single quotes in there.
SECRET_KEY = 'L0[qNV"V/oC,Kf.8+eHc`T}`BO8h-mR1uZpv;?MSc3B0>1x">b'

## -------   -------  XMPP server configuration.
S2S_PORT = 'tcp:5269:interface=0.0.0.0'
SECRET = 'secret'
DOMAIN = 'bot.example.org'
## Whether to spam the console with all the XML stanzas.
LOG_TRAFFIC = True
## Amount of django processes to spawn for XMPP-based request processing.
NWORKERS = 2


# -------   -------   -------   Defaults that should work out-of-the-box.

SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
#MEDIA_ROOT = ''
# Set MEDIA_ROOT so the project works out of the box
import os
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'snapboard/media')

# Global address of socket interface for sending XMPP messages (used by all
#  django processes and XMPP server)
# Only AF_UNIX socket for now. Non-crossplatform but somewhat easy to fix.
# Should not be relative, usually. But OK if XMPP and all django processes
#  are run in the same current dir.
SOCKET_ADDRESS = 'var/xmppoutqueue'


## sort-of optional KV storage. Read django documentation (for now) on what
## can be used here.
## Read the wiki to see what will not work without it.
#CACHE_BACKEND = 'memcached://unix:var/memcached?timeout=0'

## Simple sqlite database.
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'dev.db'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''


# SNAPBoard specific OPTIONAL settings:

# Defaults to MEDIA_URL + 'snapboard/'
SNAP_MEDIA_PREFIX = '/media'


# -------   -------   -------   General config.  Defaults can be used, but tune to your likings.

# Select your filter, the SNAPBoard default is Markdown
# Possible values: 'bbcode', 'markdown', 'textile'
SNAP_POST_FILTER = 'bbcode'

## Registration
## Note that using e-mail and, hence, activation is actually optional here.
ACCOUNT_ACTIVATION_DAYS = 5

## Avatars
AVATAR_DEFAULT_URL = "img/default_avatar.gif"
AVATAR_GRAVATAR_BACKUP = False
AVATAR_GRAVATAR_DEFAULT = "identicon"
# AVATAR_STORAGE_DIR = SNAP_MEDIA_PREFIX+"/avatars"
AVATAR_DEFAULT_SIZE = 50

## A special category for removed (hidden, censored) threads.
# (disabling not yet possible)
CAT_REMTHREADS_NAME = "Removed Threads"

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
## And pleeease, use UTC unless it's certainly and totally local forum.  --HH
TIME_ZONE = 'UTC'



# -------   -------   You need this (and urls.py) if you want to change forum address.

ROOT_URLCONF = 'urls'
ROOT_CMDCONF = 'cmds'
LOGIN_REDIRECT_URL = '/snapboard/'


# -------   -------   -------   Nothing to see below here, citizen. Move along.

## A piece for django-notification.
SITE_ID = 1

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
## ! Actually, nothing else is very well supported ATM.
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

LANGUAGES = (
    ('en', 'English'),
)

#LANGUAGE_CODE = 'fr'


# -------   -------   -------   No, really, REALLY nothing to see below here!

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #"/opt/jfu/sys/lib/python2.5/site-packages/sbextras/registration/templates",
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.markup',
    'django.contrib.sessions',
    'django.contrib.sites',
    'pagination',
    'notification',
    'registration',
    'avatar',
    'loginurl',
    'defaultsite',
    'treebeard',
    'xmppface',
    'anon',
    'snapboard',
)

from anon.settings import *

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'loginurl.backends.LoginUrlBackend',
)
        

# List of callables that know how to import templates from various sources.
# In django 1.2 cached loader can be used:
#  ('django.template.loaders.cached.Loader', (...)),
## ptftemplateloader is *almost* a must-have for XMPP(-XHTML) templates.
## And current templates are meant for it.
TEMPLATE_LOADERS = (
    'snapboard.template.ptftemplateloader.load_template_source',
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.request",
    "snapboard.views.snapboard_default_context",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',

    # django-pagination is used by the default templates
    'pagination.middleware.PaginationMiddleware',

    # SNAPBoard middleware
    'snapboard.middleware.threadlocals.ThreadLocals',

    # These are optional
    'snapboard.middleware.ban.IPBanMiddleware',
    'snapboard.middleware.ban.UserBanMiddleware',
)



# -------   -------   -------   Personalized settings overrides.
try:
    from settings_local import *
except ImportError:
    pass

# finally configure the logging with possible override.
if not LOGGING_INITIATED:
    init_logging()
