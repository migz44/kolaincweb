# Kola_app/sitemaps.py
from django.contrib.sitemaps import Sitemap
from .models import Event

class EventSitemap(Sitemap):
    changefreq = "daily"   # Google will know your events may change daily
    priority = 0.8         # Priority in sitemap (0.0 - 1.0)

    def items(self):
        # Return all events to be included in the sitemap
        return Event.objects.all()

    def lastmod(self, obj):
        # Use the event creation or updated timestamp
        return obj.created_at

    def location(self, obj):
        # Return the full URL of each event page
        return obj.get_absolute_url()
