from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Anomaly, Personnel, Zone, IncidentReport, InterrogationProtocol, NotClassifiedMaterial


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return [
            "DZ_index",
            "DZ_dashboard",
            "DZ_objects",
            "DZ_archives",
            "DZ_personnels",
            "DZ_zones",
            "DZ_organizations",
            "DZ_classifications",
            "DZ_map",
            "DZ_map_zones",
            "DZ_search",
            "DZ_silver_hand",
            "DZ_children_of_earth",
            "DZ_liberateds",
        ]

    def location(self, item):
        return reverse(item)


class ObjectSitemap(Sitemap):
    priority = 0.9

    def items(self):
        return Anomaly.objects.all()


class ArchiveSitemap(Sitemap):
    priority = 0.8

    def items(self):
        return list(IncidentReport.objects.all()) + list(InterrogationProtocol.objects.all()) + list(NotClassifiedMaterial.objects.all())


class PersonnelSitemap(Sitemap):
    priority = 0.8

    def items(self):
        return Personnel.objects.all()


class ZoneSitemap(Sitemap):
    priority = 0.8

    def items(self):
        return Zone.objects.all()