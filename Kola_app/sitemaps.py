from django.contrib.sitemaps import Sitemap
from .models import Event

class EventSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return Event.objects.all()

    def lastmod(self, obj):
        return obj.updated_at
