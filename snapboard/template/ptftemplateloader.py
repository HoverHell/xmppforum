"""
Wrapper for loading plaintextformat templates from the filesystem, e.g. with
stripping unnecessary newlines and spaces from it.
"""

import re
import sys  # Debug

from django.template import TemplateDoesNotExist
from django.template.loaders.filesystem import load_template_source \
  as load_template_source_filesystem

#from django.template.loaders.app_directories import load_template_source \
#  as load_template_source_appdir

# Might prefer to use django.template.loader.find_template_source, actually.

# Another way:
#tagspacere = re.compile('}\s\s+{')
spacere = re.compile('\s\s+')
newlinere = re.compile('\n')


def load_template_source(template_name, template_dirs=None):
    try:
        sys.stderr.write("ptftemplateloader: loading %r\n" % template_name +
          " ...from %r\n" % template_dirs)
        s, f = load_template_source_filesystem(template_name+".ptf",
          template_dirs)
        sys.stderr.write("Loaded successfully.\n")
    except Exception, e:
        sys.stderr.write("Failure: %s\n" % e)
        raise TemplateDoesNotExist, str(e)
    return (spacere.sub(u'', newlinere.sub(u'', s)), f)
load_template_source.is_usable = True
