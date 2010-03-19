"""
Wrapper for loading plaintextformat templates from the filesystem, e.g. with
stripping unnecessary newlines and spaces from it.
"""

import re
import sys  # Debug

from django.template import TemplateDoesNotExist

# Not very good but should works.
from django.template.loader import find_template_source

# Another way:
#tagspacere = re.compile('}\s\s+{')
spacere = re.compile('\s\s+')
newlinere = re.compile('\n')


def load_template_source(template_name, template_dirs=None):
    try:
        if template_name.endswith(".ptf"):
            # Really not neat hack. Avoid recursion...
            raise TemplateDoesNotExist, "not me!"
        sys.stderr.write("ptftemplateloader: loading %r\n" % template_name +
          " ...from %r\n" % template_dirs)
        s, f = find_template_source(template_name+".ptf", template_dirs)
        sys.stderr.write("Loaded successfully.\n")
    except Exception, e:
        sys.stderr.write("Failure: %s\n" % e)
        raise TemplateDoesNotExist, str(e)
    return (spacere.sub(u'', newlinere.sub(u'', s)), f)
load_template_source.is_usable = True
