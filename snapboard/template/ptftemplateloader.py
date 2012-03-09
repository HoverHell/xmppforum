""" Wrapper for loading plaintextformat templates from the filesystem, e.g. 
with stripping unnecessary newlines and spaces from it.  """

import re
import sys  # Debug

from django.template import TemplateDoesNotExist
from django.template.loader import (BaseLoader, get_template_from_string,
  find_template_loader, make_origin)

## Start templates with this to actually ptf them:
PTFTAG = u'{#ptfable#}'
PTFTAGLEN = len(PTFTAG)
## Another way:
#tagspacere = re.compile('}\s\s+{')
#SPACERE = re.compile('\s\s+')
## Hardcore-hardcore: support for 'do not remove spaces before newlines'.
SPACERE = re.compile(r'  +([^\n])')
SPACERE_SUB = ur'\1'
## Remove single newlines, turn further amount of newlines into one.
#NEWLINERE = re.compile('\n(\n?)(\n*)')
## Another possibility: strip 1 newline from each newline sequence.
NEWLINERE = re.compile(r'\n(\n*)')
NEWLINERE_SUB = ur'\1'

class Loader(BaseLoader):
    is_usable = True
    
    ## Stuff grabbed from django cache loader.
    def __init__(self, loaders):
        self._loaders = loaders
        self._cached_loaders = []
    
    # loaders = django.template.loaders.cached.Loader.loaders
    @property
    def loaders(self):
        # Resolve loaders on demand to avoid circular imports
        if not self._cached_loaders:
            for loader in self._loaders:
                self._cached_loaders.append(find_template_loader(loader))
        return self._cached_loaders

    # find_template = django.template.loaders.cached.Loader.find_template
    def find_template(self, name, dirs=None):
        for loader in self.loaders:
            try:
                template, display_name = loader.load_template_source(name, dirs)
                return (template, make_origin(display_name, loader, name, dirs))
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(name)

    def load_template_source(self, template_name, template_dirs=None):
        template, origin = self.find_template(template_name, template_dirs)
        ## Hack it up only if tagged.
        if template.startswith(PTFTAG):
            template = (
              #SPACERE.sub(SPACERE_SUB,
              #NEWLINERE.sub(NEWLINERE_SUB,
              ## Reverse:
              NEWLINERE.sub(NEWLINERE_SUB,
              SPACERE.sub(SPACERE_SUB,
              template[PTFTAGLEN:])))
            # Removing tag is optional if it's valid template, though.
        return (template, origin)
    load_template_source.is_usable = True


## compatibility impossible?
#_loader = Loader()
## Or can make some hack like
#_loader = Loader(settings.TEMPLATE_LOADERS
## ?  Perhaps just unnecessary.
## But, also, can return the previous form of this loader mayhaps.

#def load_template_source(template_name, template_dirs=None):
#    # For backwards compatibility
#    return _loader.load_template_source(template_name, template_dirs)
#load_template_source.is_usable = True
