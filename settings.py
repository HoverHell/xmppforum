# -*- coding: utf-8 -*-
# Django settings for examplesite project.

# Debug mode.
DEBUG = False
TEMPLATE_DEBUG = DEBUG

## There's not very much static, so it should be appropriate to serve it
## over django; however, you might want to set up some other webserver to do
## that (and disabling this option isn't very necessary afterwards, just set
## the MEDIA_URL).
SERVE_STATIC = True

# Make this unique, and don't share it with anybody.
# `pwgen -sy 50 1`, yet beware of single quotes in there.
SECRET_KEY = 'L0[qNV"V/oC,Kf.8+eHc`T}`BO8h-mR1uZpv;?MSc3B0>1x">b'
## Security cookie for XMPP-to-django-over-HTTP-POST-JSON transport.
## * NOTE: if not defined (empty), multiprocessing workers are used.
POSTCOOKIE = ''

## URL for POSTing the JSON from XMPP.
POSTURL = 'http://127.0.0.1:8000/_xmpp/postdata'

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
## Defaults to your machine's hostname,
## but http:// is supposedly necessary.
#SITE_DOMAIN = 'http://example.com'
## The site's name. Defaults to 'defaultsite' otherwise.
SITE_NAME = 'xmppforum'


# -------   -------   -------   Addresses and stuff. Almost certainly have to be changed.

DEFAULT_FROM_EMAIL = "jfu@localhost"



# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
# Full URI required for XMPP images to have any chances of working.
#MEDIA_URL = 'http://localhost:8000/media/'
MEDIA_URL = '/m/'

# SNAPBoard-specific media files path.
#SNAP_MEDIA_PREFIX = MEDIA_URL  ## Default.

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

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


## Sort-of optional KV storage. Read django documentation (for now) on what
##  can be used here.
## Read the xmppforum wiki to see what will not work without it.
## ! This one changed in django 1.3
## If running on localhost, using unix file-socket is advised.
#CACHE_BACKEND = 'memcached://unix:var/memcached?timeout=0'
## If you're using a default system-wide installation of memcached, most
## likely you need:
#CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
## By default a thread-local locmem:// backend is used (most likely).

## Simple sqlite database.
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'dev.db'
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

## To use postgresql in a default system-wide installation, you can simply
## redefine:
#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = ''  # username is used if empty.
## Additionally, if you're running a user-local postgresql instance, tou
## need to specify path to its datadir:
#DATABASE_HOST = '/path/to/datadir'
#DATABASE_PORT = '5443'
## Username and password are generally only needed when using postgresql
## over network.


# -------   -------   -------   General config.  Defaults can be used, but tune to your likings.

# Select your filter, the SNAPBoard default is Markdown
# Possible values: 'bbcode', 'markdown', 'textile'
## ! Currently, only bbcode might be properly supported.
SNAP_POST_FILTER = 'bbcode'

## Registration
## Note that using e-mail and, hence, activation is actually optional here.
ACCOUNT_ACTIVATION_DAYS = 5

## Avatars
AVATAR_DEFAULT_URL = ""
AVATAR_GRAVATAR_BACKUP = False
AVATAR_GRAVATAR_DEFAULT = "identicon"
AVATAR_STORAGE_DIR = "up"  # UserPic
AVATAR_DEFAULT_SIZE = 50


### timedelta parameters.
## display names for all time periods. Empty ones are not used.
#TIMEDELTA_NAMES = (' yr', ' mon', ' wk', ' day', ' hr', ' min', ' sec')
#TIMEDELTA_NAMES = ('y', 'mo', 'w', 'd', 'h', 'm', '')  # default.
## Maximal amount of non-zero periods to display (0 - all)
#TIMEDELTA_MAXLEN = 2
#TIMEDELTA_MAXLEN = 0  # default.

### A special category for removed (hidden, censored) threads.
## (disabling not yet possible)
CAT_REMTHREADS_NAME = "Removed Threads"

# Local time zone for this installation. All choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
## And pleeease, use UTC unless it's certainly and totally local forum.  --HH
TIME_ZONE = 'UTC'



# -------   -------   You need this (and urls.py) if you want to change forum address.

ROOT_URLCONF = 'urls'
ROOT_CMDCONF = 'cmds'
LOGIN_REDIRECT_URL = '/'


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
# * At least something in here requires django 1.2 at least.
_lp = lambda lo, *ar: (lo, ar,)  # loader, arguments
TEMPLATE_LOADERS = (
  _lp('django.template.loaders.cached.Loader',  # cache
    _lp('snapboard.template.ptftemplateloader.Loader',  # ptf
     'django.template.loaders.filesystem.Loader',
     'django.template.loaders.app_directories.Loader',
     #'django.template.loaders.eggs.load_template_source'
    ),  # ptf
  ),  # cache
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
