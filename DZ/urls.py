from django.urls import path
from .views import *
import DZ.api.views


urlpatterns = [
    path('', index, name='DZ_index'),
    path('dashboard/', dashboard, name="DZ_dashboard"),
    
    path('objects/', objects, name="DZ_objects"),
    path('object/<slug:slug>', object_detail, name="DZ_object"),

    path('archives/', archives, name='DZ_archives'),
    path('archive/<slug:slug>', archive, name='DZ_archive'),

    path('personnels/', personnels, name='DZ_personnels'),
    path('personnel/<slug:slug>', personnel, name='DZ_personnel'),

    path('zones/', zones, name='DZ_zones'),
    path('zone/<slug:slug>/', zone, name='DZ_zone'),

    path('organizations/', organizations, name='DZ_organizations'),
    path('organization/silver_hand/', silver_hand, name='DZ_silver_hand'),
    path('organization/children_of_earth/', children_of_earth, name='DZ_children_of_earth'),
    path('organization/liberateds/', liberateds, name='DZ_liberateds'),

    path('classifications/', classifications, name='DZ_classifications'),

    path('map/', map_view, name='DZ_map'),
    path('map/zones/', map_zones, name='DZ_map_zones'),

    path('search/', search, name='DZ_search'),

    # api for ai:
    path('api/urls/', DZ.api.views.api_urls, name='DZ_urls'),
    path('api/anomalies/', DZ.api.views.api_anomalies, name='api_anomalies'),
    path('api/anomaly/<slug:slug>/', DZ.api.views.api_anomaly_detail, name='api_anomaly_detail'),
    path('api/personnels/', DZ.api.views.api_personnels, name='api_personnels'),
    path('api/personnel/<slug:slug>/', DZ.api.views.api_personnel_detail, name='api_personnel_detail'),
    path('api/zones/', DZ.api.views.api_zones, name='api_zones'),
    path('api/zone/<slug:slug>/', DZ.api.views.api_zone_detail, name='api_zone_detail'),
    path('api/organizations/', DZ.api.views.api_organizations, name='api_organizations'),
    path('api/organization/<slug:slug>/', DZ.api.views.api_organization_detail, name='api_organization_detail'),
    path('api/archives/', DZ.api.views.api_archives, name='api_archives'),
    path('api/archive/<slug:slug>/', DZ.api.views.api_archive_detail, name='api_archive_detail'),
    path('api/search/', DZ.api.views.api_search, name='api_search'),
    path('api/classifications/', DZ.api.views.classifications, name='api_classifications'),
]