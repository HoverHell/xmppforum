from django.contrib.sites.models import Site
from django.contrib.syndication.feeds import Feed
from django.utils.translation import ugettext_lazy as _

from snapboard.models import Post


SITE = Site.objects.get_current()

class LatestPosts(Feed):
    title = _('%s Latest Discussions') % str(SITE)
    link = "/snapboard/"
    description = _("The latest contributions to discussions.")

    title_template = "snapboard/feeds/latest_title.html"
    description_template = "snapboard/feeds/latest_description.html"

    def items(self):
        # we should only return the non-private messages
        return Post.objects.exclude(private__isnull=False).order_by('-date')[:10]

# vim: ai ts=4 sts=4 et sw=4
