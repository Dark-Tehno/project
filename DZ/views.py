from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from itertools import chain
from django.urls import reverse
from django.http import Http404

from .models import *


# Create your views here.
def index(request):
    return render(request, 'DZ/index.html')

def dashboard(request):
    return render(request, 'DZ/dashboard.html')


def objects(request):
    anomalys = Anomaly.objects.all()
    return render(request, 'DZ/objects/objects_list.html', {'anomalys': anomalys})

def object_detail(request, slug):
    anomaly = Anomaly.objects.get(slug=slug)
    return render(request, 'DZ/objects/object_detail.html', {'anomaly': anomaly})


def archives(request):
    incident_reports = IncidentReport.objects.all()
    interrogation_protocols = InterrogationProtocol.objects.all()
    not_classified_materials = NotClassifiedMaterial.objects.all()

    archive_materials = sorted(
        chain(incident_reports, interrogation_protocols, not_classified_materials),
        key=lambda x: x.date,
        reverse=True
    )

    if request.GET.get('format') == 'json':
        data = []
        for item in archive_materials:
            item_data = {
                'name': item.name,
                'date': item.date.isoformat(),
                'slug': item.slug,
                'type': item.get_material_type(),
                'url': reverse('DZ_archive', kwargs={'slug': item.slug})
            }

            if isinstance(item, IncidentReport):
                item_data['content'] = {
                    'description': item.description,
                    'course_of_events': item.course_of_events,
                    'consequences': item.consequences,
                }
            elif isinstance(item, InterrogationProtocol):
                item_data['content'] = {
                    'interrogator': item.interrogator,
                    'interrogated_person': item.interrogated_person,
                    'dialogue': item.dialogue,
                }
            elif isinstance(item, NotClassifiedMaterial):
                item_data['content'] = {'data': item.data}
            
            data.append(item_data)
        return JsonResponse({'archive_materials': data})

    return render(request, 'DZ/archives/archive_list.html', {'archive_materials': archive_materials})

def archive(request, slug):
    try:
        archive_item = IncidentReport.objects.get(slug=slug)
        template_name = 'DZ/archives/incident_report_detail.html'
    except IncidentReport.DoesNotExist:
        try:
            archive_item = InterrogationProtocol.objects.get(slug=slug)
            template_name = 'DZ/archives/interrogation_protocol_detail.html'
        except InterrogationProtocol.DoesNotExist:
            try:
                archive_item = NotClassifiedMaterial.objects.get(slug=slug)
                template_name = 'DZ/archives/not_classified_material_detail.html'
            except NotClassifiedMaterial.DoesNotExist:
                raise Http404("Archive item not found")
    
    context = {
        'archive_item': archive_item
    }
    return render(request, template_name, context)


def personnels(request):
    personnels = Personnel.objects.all()
    return render(request, 'DZ/personnels/personnel_list.html', {'personnels': personnels.order_by('name')})

def personnel(request, slug):
    personnel = get_object_or_404(Personnel, slug=slug)
    return render(request, 'DZ/personnels/personnel_detail.html', {'personnel': personnel})


def zones(request):
    zones = Zone.objects.all()
    return render(request, 'DZ/zones/zone_list.html', {'zones': zones.order_by('name')})

def zone(request, slug):
    zone = get_object_or_404(Zone, slug=slug)
    return render(request, 'DZ/zones/zone_detail.html', {'zone': zone})


def organizations(request):
    return render(request, 'DZ/organizations/organizations_list.html')

def silver_hand(request):
    return render(request, 'DZ/organizations/silver_hand.html')

def children_of_earth(request):
    return render(request, 'DZ/organizations/children_of_earth.html')

def liberateds(request):
    return render(request, 'DZ/organizations/liberateds.html')


def classifications(request):
    return render(request, 'DZ/classifications/classifications.html')


def map_view(request):
    return render(request, 'DZ/map/map.html')

def map_zones(request):
    zones = Zone.objects.all()
    zones_data = [
        {'name': zone.name, 'x': zone.x, 'y': zone.y, 'link': zone.get_absolute_url()}
        for zone in zones
    ]
    return JsonResponse({'zones': zones_data})


def search(request):
    query = request.GET.get('query', '')
    context = {'query': query}

    if query:
        # Поиск по Зонам
        zone_query = (Q(name__icontains=query) |
                      Q(location__icontains=query) |
                      Q(description__icontains=query) |
                      Q(specialization__icontains=query))
        zones_results = Zone.objects.filter(zone_query)

        # Поиск по Аномалиям
        anomaly_query = (Q(name__icontains=query) |
                         Q(description__icontains=query) |
                         Q(anomalous_properties__icontains=query))
        anomalies_results = Anomaly.objects.filter(anomaly_query)

        # Поиск по Персоналу
        personnel_query = (Q(name__icontains=query) |
                           Q(callsign__icontains=query) |
                           Q(position__icontains=query) |
                           Q(biography__icontains=query) |
                           Q(psych_profile__icontains=query))
        personnel_results = Personnel.objects.filter(personnel_query)

        # Поиск по Отчетам об инцидентах
        incident_report_query = (Q(name__icontains=query) |
                                 Q(description__icontains=query) |
                                 Q(consequences__icontains=query))
        incident_reports_results = IncidentReport.objects.filter(incident_report_query)

        # Поиск по Протоколам допросов
        interrogation_protocol_query = (Q(name__icontains=query) |
                                        Q(interrogator__icontains=query) |
                                        Q(interrogated_person__icontains=query) |
                                        Q(dialogue__icontains=query))
        interrogation_protocols_results = InterrogationProtocol.objects.filter(interrogation_protocol_query)

        # Поиск по Неклассифицированным материалам
        not_classified_material_query = (Q(name__icontains=query) | Q(data__icontains=query))
        not_classified_materials_results = NotClassifiedMaterial.objects.filter(not_classified_material_query)

        context.update({
            'zones_results': zones_results,
            'anomalies_results': anomalies_results,
            'personnel_results': personnel_results,
            'incident_reports_results': incident_reports_results,
            'interrogation_protocols_results': interrogation_protocols_results,
            'not_classified_materials_results': not_classified_materials_results,
        })

    return render(request, 'DZ/search.html', context)