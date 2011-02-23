""" Wrapper for loading plaintextformat templates from the filesystem, e.g. 
with stripping unnecessary newlines and spaces from it.  """

import re
import sys  # Debug

from django.template import TemplateDoesNotExist
from django.template.loader import BaseLoader

# Not very good but should works.
from django.template.loader import find_template_source

# Another way:
#tagspacere = re.compile('}\s\s+{')
spacere = re.compile('\s\s+')
newlinere = re.compile('\n')

class Loader(BaseLoader):
    is_usable = True

    def load_template_source(self, template_name, template_dirs=None):
        try:
            # ! XXX / TODO / FIXME: invert this check to use this loader
            #  only for template names that explicitly end with '.ptf'!
            if template_name.endswith(".ptf"):
                # Really not neat hack. Avoid recursion...
                raise TemplateDoesNotExist, "Already ptf requested."
            s, f = find_template_source(template_name+".ptf", template_dirs)
        except Exception, e:
            raise TemplateDoesNotExist, str(e)
        return (spacere.sub(u'', newlinere.sub(u'', s)), f)
    load_template_source.is_usable = True


_loader = Loader()

def load_template_source(template_name, template_dirs=None):
    # For backwards compatibility
    return _loader.load_template_source(template_name, template_dirs)
load_template_source.is_usable = True
