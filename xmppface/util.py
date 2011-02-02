""" Various utility functions for both internal and external use. Might get
moved (grouped) somewhere else.  """

# cmdresolver / urlresolver hack.
# ! XXX: Does not work well yet: url() at django.conf.urls.defaults uses
#  explicit RegexURLResolver for include()'d patterns.
from django.core.urlresolvers import RegexURLResolver


class RegexCmdResolver(RegexURLResolver):
    """ A small hack of RegexURLResolver for 'urlpatterns' -> 'cmdpatterns'
    rename. """
    
    def _get_url_patterns(self):
        patterns = getattr(self.urlconf_module, "cmdpatterns",
            self.urlconf_module)
        try:
            iter(patterns)
        except TypeError:
            raise ImproperlyConfigured("The included cmdconf %s doesn't "
              " have any patterns in it" % self.urlconf_name)
        return patterns
    
    url_patterns = property(_get_url_patterns)
