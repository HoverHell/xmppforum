"""
Wrapper for loading plaintextformat templates from the filesystem, e.g. with
stripping unnecessary newlines and spaces from it.
"""

import re

from django.template.loaders.filesystem import load_template_source \
  as load_template_source_filesystem

#from django.template.loaders.app_directories import load_template_source \
#  as load_template_source_appdir

# Might prefer to use django.template.loader.find_template_source, actually.

spacere = re.compile('\s\s+')
newlinere = re.compile('\n')


def load_template_source(template_name, template_dirs=None):
    s = load_template_source_filesystem(template_name, template_dirs)
    return spacere.sub(u'', newlinere.sub(u'', s))

load_template_source.is_usable = True
