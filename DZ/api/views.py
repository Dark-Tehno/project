from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from DZ.models import *
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.db.models import Q


urls = {
    'Страница входа': {
        'url': '/DZ/',
        'description': 'Страница входа в систему организации для входа нужно ввести `login` или `connect`, имеются пасхалки с командами: `ls`, `dir`, `help`, `?`, `whoami`, `sudo`, `su`, `exit`, `quit`, `clear`, `cls`.'
    },
    'Панель управления': {
        'url': '/DZ/dashboard/',
        'description': 'Панель управления, на которой можно перейти на все страницы(`/DZ/search/`, `/DZ/archives/`, `/DZ/objects/`, `/DZ/personnels/`, `/DZ/zones/`, `/DZ/organizations/`, `/DZ/classifications/`, `/DZ/map/`) с данными организации.'
    },
    'Список аномалий': {
        'url': '/DZ/objects/',
        'description': 'Список всех зарегистрированных аномалий.'
    },
    'Детальная страница аномалии': {
        'url': '/DZ/object/<slug>/',
        'description': 'Детальная информация по конкретной аномалии, где <slug> - это уникальный идентификатор аномалии.'
    },
    'Архив материалов': {
        'url': '/DZ/archives/',
        'description': 'Общий архив всех материалов: отчётов об инцидентах, протоколов допросов и неклассифицированных материалов.'
    },
    'Детальная страница архивного материала': {
        'url': '/DZ/archive/<slug>/',
        'description': 'Детальная информация по конкретному архивному материалу, где <slug> - это уникальный идентификатор материала.'
    },
    'Список персонала': {
        'url': '/DZ/personnels/',
        'description': 'Список всех сотрудников организации.'
    },
    'Детальная страница сотрудника': {
        'url': '/DZ/personnel/<slug>/',
        'description': 'Детальная информация по конкретному сотруднику, где <slug> - это уникальный идентификатор сотрудника.'
    },
    'Список зон': {
        'url': '/DZ/zones/',
        'description': 'Список всех зон организации.'
    },
    'Детальная страница зоны': {
        'url': '/DZ/zone/<slug>/',
        'description': 'Детальная информация по конкретной зоне, где <slug> - это уникальный идентификатор зоны.'
    },
    'Список организаций': {
        'url': '/DZ/organizations/',
        'description': 'Список всех известных организаций.'
    },
    'Организация "Серебряная Рука"': {
        'url': '/DZ/organization/silver_hand/',
        'description': 'Информация об организации "Серебряная Рука".'
    },
    'Организация "Дети Земли"': {
        'url': '/DZ/organization/children_of_earth/',
        'description': 'Информация об организации "Дети Земли".'
    },
    'Организация "Освобождённые"': {
        'url': '/DZ/organization/liberateds/',
        'description': 'Информация об организации "Освобождённые".'
    },
    'Классификации': {
        'url': '/DZ/classifications/',
        'description': 'Информация о различных классификациях, используемых в организации.'
    },
    'Карта': {
        'url': '/DZ/map/',
        'description': 'Интерактивная карта с расположением зон.'
    },
    'API зон для карты': {
        'url': '/DZ/map/zones/',
        'description': 'API-эндпоинт, возвращающий данные о зонах для отображения на карте в формате JSON.'
    },
    'Поиск': {
        'url': '/DZ/search/',
        'description': 'Страница поиска по всем материалам организации.'
    },
    'API URL-ов': {
        'url': '/DZ/api/urls/',
        'description': 'API-эндпоинт, возвращающий список всех доступных URL-ов и их описания в формате JSON.'
    },
    'API аномалий': {
        'url': '/DZ/api/anomalies/',
        'description': 'API-эндпоинт, возвращающий список всех аномалий в формате JSON.'
    },
    'API детальной информации об аномалии': {
        'url': '/DZ/api/anomaly/<slug>/',
        'description': 'API-эндпоинт, возвращающий детальную информацию о конкретной аномалии в формате JSON.'
    },
    'API персонала': {
        'url': '/DZ/api/personnels/',
        'description': 'API-эндпоинт, возвращающий список всего персонала в формате JSON.'
    },
    'API детальной информации о сотруднике': {
        'url': '/DZ/api/personnel/<slug>/',
        'description': 'API-эндпоинт, возвращающий детальную информацию о конкретном сотруднике в формате JSON.'
    },
    'API зон': {
        'url': '/DZ/api/zones/',
        'description': 'API-эндпоинт, возвращающий список всех зон в формате JSON.'
    },
    'API детальной информации о зоне': {
        'url': '/DZ/api/zone/<slug>/',
        'description': 'API-эндпоинт, возвращающий детальную информацию о конкретной зоне в формате JSON.'
    },
    'API организаций': {
        'url': '/DZ/api/organizations/',
        'description': 'API-эндпоинт, возвращающий список всех известных организаций и ссылки на их детальные страницы в формате JSON.'
    },
    'API информации об организации': {
        'url': '/DZ/api/organization/<slug>/',
        'description': 'API-эндпоинт, возвращающий информацию об определенной организации в формате JSON.'
    },
    'API архивов': {
        'url': '/DZ/api/archives/',
        'description': 'API-эндпоинт, возвращающий список всех архивных материалов (отчётов об инцидентах, протоколов допросов, неклассифицированных материалов) в формате JSON.'
    },
    'API детальной информации об архивном материале': {
        'url': '/DZ/api/archive/<slug>/',
        'description': 'API-эндпоинт, возвращающий детальную информацию о конкретном архивном материале в формате JSON.'
    },
    'API поиска': {
        'url': '/DZ/api/search/',
        'description': 'API-эндпоинт, возвращающий результаты поиска по всем материалам в формате JSON.'
    }
}

@api_view(['GET'])
def api_urls(request):
    return Response(urls)


@api_view(['GET'])
def api_anomalies(request):
    anomalies = Anomaly.objects.all()
    data = []
    for anomaly in anomalies:
        data.append({
            'id_prefix': anomaly.id_prefix,
            'id_number': anomaly.id_number,
            'name': anomaly.name,
            'threat_class': anomaly.threat_class,
            'description': anomaly.description,
            'anomalous_properties': anomaly.anomalous_properties,
            'containment_zone': anomaly.containment_zone.name if anomaly.containment_zone else None,
            'image': request.build_absolute_uri(anomaly.image.url) if anomaly.image else None,
            'image_caption': anomaly.image_caption,
            'slug': anomaly.slug,
            'url': request.build_absolute_uri(anomaly.get_absolute_url()),
        })
    return Response(data)


@api_view(['GET'])
def api_anomaly_detail(request, slug):
    anomaly = get_object_or_404(Anomaly, slug=slug)
    data = {
        'id_prefix': anomaly.id_prefix,
        'id_number': anomaly.id_number,
        'name': anomaly.name,
        'threat_class': anomaly.threat_class,
        'description': anomaly.description,
        'anomalous_properties': anomaly.anomalous_properties,
        'containment_zone': anomaly.containment_zone.name if anomaly.containment_zone else None,
        'image': request.build_absolute_uri(anomaly.image.url) if anomaly.image else None,
        'image_caption': anomaly.image_caption,
        'slug': anomaly.slug,
        'url': request.build_absolute_uri(anomaly.get_absolute_url()),
    }
    return Response(data)


@api_view(['GET'])
def api_personnels(request):
    personnels = Personnel.objects.all()
    data = []
    for personnel in personnels:
        data.append({
            'name': personnel.name,
            'callsign': personnel.callsign,
            'personnel_class': personnel.personnel_class,
            'position': personnel.position,
            'status': personnel.status,
            'biography': personnel.biography,
            'psych_profile': personnel.psych_profile,
            'quote': personnel.quote,
            'service_marks': personnel.service_marks,
            'image': request.build_absolute_uri(personnel.image.url) if personnel.image else None,
            'slug': personnel.slug,
            'url': request.build_absolute_uri(personnel.get_absolute_url()),
        })
    return Response(data)


@api_view(['GET'])
def api_personnel_detail(request, slug):
    personnel = get_object_or_404(Personnel, slug=slug)
    data = {
        'name': personnel.name,
        'callsign': personnel.callsign,
        'personnel_class': personnel.personnel_class,
        'position': personnel.position,
        'status': personnel.status,
        'biography': personnel.biography,
        'psych_profile': personnel.psych_profile,
        'quote': personnel.quote,
        'service_marks': personnel.service_marks,
        'image': request.build_absolute_uri(personnel.image.url) if personnel.image else None,
        'slug': personnel.slug,
        'url': request.build_absolute_uri(personnel.get_absolute_url()),
    }
    return Response(data)


@api_view(['GET'])
def api_zones(request):
    zones = Zone.objects.all()
    data = []
    for zone in zones:
        data.append({
            'name': zone.name,
            'location': zone.location,
            'status': zone.status,
            'commander': zone.commander.name if zone.commander else None,
            'description': zone.description,
            'specialization': zone.specialization,
            'command_staff': zone.command_staff,
            'scientific_staff': zone.scientific_staff,
            'security_personnel': zone.security_personnel,
            'administrative_technical_staff': zone.administrative_technical_staff,
            'class_a_personnel': zone.class_a_personnel,
            'x': zone.x,
            'y': zone.y,
            'slug': zone.slug,
            'url': request.build_absolute_uri(zone.get_absolute_url()),
        })
    return Response(data)


@api_view(['GET'])
def api_zone_detail(request, slug):
    zone = get_object_or_404(Zone, slug=slug)
    data = {
        'name': zone.name,
        'location': zone.location,
        'status': zone.status,
        'commander': zone.commander.name if zone.commander else None,
        'description': zone.description,
        'specialization': zone.specialization,
        'command_staff': zone.command_staff,
        'scientific_staff': zone.scientific_staff,
        'security_personnel': zone.security_personnel,
        'administrative_technical_staff': zone.administrative_technical_staff,
        'class_a_personnel': zone.class_a_personnel,
        'x': zone.x,
        'y': zone.y,
        'slug': zone.slug,
        'url': request.build_absolute_uri(zone.get_absolute_url()),
    }
    return Response(data)


@api_view(['GET'])
def api_organizations(request):
    return Response({
        'silver_hand': {
            'url': request.build_absolute_uri(reverse('DZ_silver_hand')),
            'slug': 'silver_hand',
            'description': 'Информация об организации "Серебряная Рука".'
        },
        'children_of_earth': {
            'url': request.build_absolute_uri(reverse('DZ_children_of_earth')),
            'slug': 'children_of_earth',
            'description': 'Информация об организации "Дети Земли".'
        },
        'liberateds': {
            'url': request.build_absolute_uri(reverse('DZ_liberateds')),
            'slug': 'liberateds',
            'description': 'Информация об организации "Освобождённые".'
        },
    })


@api_view(['GET'])
def api_organization_detail(request, slug):
    org_data = {
        'silver_hand': {
            'name': 'Серебряная Длань',
            'type': 'Транснациональная корпорация',
            'ideology': 'Радикальный техно-капитализм. "Всё имеет свою цену".',
            'status': 'Враждебная / Конкурирующая',
            'general_info': {
                'public_facade': 'Легальный бизнес в сфере высоких технологий, фармацевтики и частного консалтинга.',
                'secret_activity': 'Поиск, захват, изучение и коммерциализация аномалий и аномальных технологий.'
            },
            'structure': {
                'description': 'Построена по модели безжалостной, но эффективной мегакорпорации, где царит культура "внутренней конкуренции". Успех вознаграждается, а провал — карается, часто фатально.',
                'departments': [
                    {
                        'name': 'Совет Директоров',
                        'description': 'Анонимный коллектив, состоящий из богатейших и влиятельнейших людей планеты. Ставят цели по прибыли.'
                    },
                    {
                        'name': 'Исполнительный Комитет',
                        'description': 'Реальная власть. Несколько вице-президентов, курирующих свои направления.'
                    },
                    {
                        'name': 'Департамент Приобретения Активов (AAD)',
                        'description': '"Полевые" команды, занимающиеся шпионажем и силовым захватом аномалий.'
                    },
                    {
                        'name': 'Департамент Исследований и Применения (R&A)',
                        'description': 'Лаборатории, где аномалии "разбирают на запчасти" для создания коммерческих продуктов.'
                    },
                    {
                        'name': 'Департамент Монетизации и Продаж',
                        'description': 'Отдел, отвечающий за продажу аномальных технологий на черном рынке.'
                    },
                    {
                        'name': 'Департамент Внутренних Дел',
                        'description': 'Жестокая служба безопасности, пресекающая шпионаж и гарантирующая лояльность сотрудников.'
                    }
                ]
            },
            'relations': {
                'children_of_earth': 'Считают "Детей Земли" и SCP-Фонд "собаками на сене", которые сидят на сокровищнице и мешают прогрессу (и прибыли). Являются основной угрозой в сфере промышленного шпионажа и кражи активов.'
            },
            'url': request.build_absolute_uri(reverse('DZ_silver_hand')),
        },
        'children_of_earth': {
            'name': 'Дети Земли',
            'type': 'Секретная глобальная организация',
            'ideology': 'Сдерживание и защита человечества.',
            'status': 'Активна',
            'general_info': {
                'public_facade': 'Отсутствует. Организация действует в полной секретности, поддерживая "Маскарад".',
                'main_goal': 'Защита человечества от аномальных угроз, а также от враждебных организаций. Деятельность включает поиск, сдерживание, изучение и, при необходимости, нейтрализацию аномалий.'
            },
            'structure': {
                'description': 'Иерархия в организации "Дети Земли" строго регламентирована и разделена на классы по буквенному обозначению от A до Z-2. Эта система определяет полномочия, обязанности и уровень допуска каждого сотрудника.',
                'levels': [
                    {
                        'name': 'Низшие классы (A-E)',
                        'description': 'Включают расходный персонал, службу безопасности, разведку и отдел информационной безопасности ("Затирщики").'
                    },
                    {
                        'name': 'Научный и оперативный персонал (F-N)',
                        'description': 'Ядро организации, состоящее из учёных, полевых агентов, групп быстрого реагирования и охраны объектов. Включает также аномальных сотрудников (Класс N), работающих на благо организации.'
                    },
                    {
                        'name': 'Командный состав (M-W)',
                        'description': 'Военное и административное руководство, управляющее отделами, Зонами содержания и глобальными операциями.'
                    },
                    {
                        'name': 'Высшее руководство (X, Z-1, Z-2)',
                        'description': 'Высший совет Z-1, управляющий всей организацией, и таинственный Основатель (Z-2), являющийся высшей инстанцией.'
                    }
                ]
            },
            'relations': {
                'scp_foundation': 'Стратегические союзники. Организации координируют действия и обмениваются информацией.',
                'silver_hand': 'Враги / Конкуренты. "Длань" стремится к коммерциализации аномалий, что противоречит целям "Детей Земли". Ведётся постоянная контрразведывательная деятельность.',
                'liberateds': 'Идеологические противники. Рассматриваются как террористическая угроза из-за их стремления "освободить" все аномалии, что приводит к атакам на Зоны содержания.'
            },
            'url': request.build_absolute_uri(reverse('DZ_children_of_earth')),
        },
        'liberateds': {
            'name': 'Освобождённые',
            'type': 'Децентрализованная сеть идеологических ячеек',
            'ideology': 'Радикальный аномальный трансгуманизм. "Сдерживание — это рабство. Аномалия — это право по рождению".',
            'status': 'Идеологические противники / Террористическая угроза',
            'general_info': {
                'public_facade': 'Отсутствует. Действуют через анонимные онлайн-сообщества, пропагандистские каналы и сарафанное радио в аномальном андеграунде.',
                'main_goal': 'Полное уничтожение "Маскарада". "Освобождённые" верят, что сдерживание аномалий — это искусственный барьер, мешающий человечеству и аномалиям слиться в единую, высшую форму жизни.'
            },
            'structure': {
                'description': 'Не имеют чёткой иерархии. Организованы как повстанческое движение, где разные группы выполняют свои функции, объединённые общей идеей.',
                'key_figure': {
                    'name': 'Пророк',
                    'description': 'Идеологический лидер и центральный узел движения. Предположительно, аномальная информационная сущность в глобальной сети, направляющая последователей через "пророчества".'
                },
                'factions': [
                    {
                        'name': '"Глашатаи" (Пропагандисты)',
                        'description': 'Занимаются вербовкой, распространением идеологии и хактивизмом. Активно пытаются переманить на свою сторону сотрудников Класса N.'
                    },
                    {
                        'name': '"Пастыри" (Проводники)',
                        'description': 'Организуют подпольную сеть для помощи сбежавшим или "пробудившимся" аномалиям.'
                    },
                    {
                        'name': '"Воины Зари" (Боевые ячейки)',
                        'description': 'Силовые группы, чья главная цель — нарушение условий содержания и "освобождение" аномалий путём атак на Зоны содержания.'
                    }
                ]
            },
            'threat_assessment': 'Представляют непредсказуемую и асимметричную угрозу. Их децентрализованная структура и фанатичная преданность идее делают их крайне опасными. С ними невозможно вести переговоры, а их действия часто приводят к огромным жертвам.',
            'url': request.build_absolute_uri(reverse('DZ_liberateds')),
        },
    }
    
    organization = org_data.get(slug)
    if organization:
        return Response(organization)
    else:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
@api_view(['GET'])
def api_archives(request):
    incident_reports = IncidentReport.objects.all()
    interrogation_protocols = InterrogationProtocol.objects.all()
    not_classified_materials = NotClassifiedMaterial.objects.all()

    data = []
    for item in incident_reports:
        data.append({
            'type': 'incident_report',
            'name': item.name,
            'date': item.date.isoformat(),
            'anomaly': item.anomaly.name,
            'description': item.description,
            'course_of_events': item.course_of_events,
            'consequences': item.consequences,
            'slug': item.slug,
            'url': request.build_absolute_uri(reverse('DZ_archive', kwargs={'slug': item.slug})),
        })
    for item in interrogation_protocols:
        data.append({
            'type': 'interrogation_protocol',
            'name': item.name,
            'date': item.date.isoformat(),
            'anomaly': item.anomaly.name,
            'interrogator': item.interrogator,
            'interrogated_person': item.interrogated_person,
            'dialogue': item.dialogue,
            'slug': item.slug,
            'url': request.build_absolute_uri(reverse('DZ_archive', kwargs={'slug': item.slug})),
        })
    for item in not_classified_materials:
        data.append({
            'type': 'not_classified_material',
            'name': item.name,
            'date': item.date.isoformat(),
            'anomaly': item.anomaly.name,
            'data': item.data,
            'slug': item.slug,
            'url': request.build_absolute_uri(reverse('DZ_archive', kwargs={'slug': item.slug})),
        })
    return Response(data)


@api_view(['GET'])
def api_archive_detail(request, slug):
    try:
        archive_item = IncidentReport.objects.get(slug=slug)
        item_type = 'incident_report'
        
    except IncidentReport.DoesNotExist:
        try:
            archive_item = InterrogationProtocol.objects.get(slug=slug)
            item_type = 'interrogation_protocol'
        except InterrogationProtocol.DoesNotExist:
            try:
                archive_item = NotClassifiedMaterial.objects.get(slug=slug)
                item_type = 'not_classified_material'
            except NotClassifiedMaterial.DoesNotExist:
                return Response({'error': 'Archive item not found'}, status=status.HTTP_404_NOT_FOUND)

    data = {
        'type': item_type,
        'name': archive_item.name,
        'date': archive_item.date.isoformat(),
        'anomaly': archive_item.anomaly.name,
        'slug': archive_item.slug,
        'url': request.build_absolute_uri(reverse('DZ_archive', kwargs={'slug': archive_item.slug})),
    }

    if item_type == 'incident_report':
        data.update({
            'description': archive_item.description,
            'course_of_events': archive_item.course_of_events,
            'consequences': archive_item.consequences,
        })
    elif item_type == 'interrogation_protocol':
        data.update({
            'interrogator': archive_item.interrogator,
            'interrogated_person': archive_item.interrogated_person,
            'dialogue': archive_item.dialogue,
        })
    elif item_type == 'not_classified_material':
        data.update({
            'data': archive_item.data,
        })
    return Response(data)
    

@api_view(['GET'])
def api_search(request):
    query = request.GET.get('query', '')
    results = []

    if query:
        # Поиск по Зонам
        zone_query = (Q(name__icontains=query) |
                      Q(location__icontains=query) |
                      Q(description__icontains=query) |
                      Q(specialization__icontains=query))
        zones_results = Zone.objects.filter(zone_query)
        for item in zones_results:
            results.append({
                'type': 'zone',
                'name': item.name,
                'description': item.description,
                'url': request.build_absolute_uri(item.get_absolute_url()),
            })

        # Поиск по Аномалиям
        anomaly_query = (Q(name__icontains=query) |
                         Q(description__icontains=query) |
                         Q(anomalous_properties__icontains=query))
        anomalies_results = Anomaly.objects.filter(anomaly_query)
        for item in anomalies_results:
            results.append({
                'type': 'anomaly',
                'name': item.name,
                'description': item.description,
                'url': request.build_absolute_uri(reverse('DZ_object', kwargs={'slug': item.slug})),
            })

        # Поиск по Персоналу
        personnel_query = (Q(name__icontains=query) |
                           Q(callsign__icontains=query) |
                           Q(position__icontains=query) |
                           Q(biography__icontains=query) |
                           Q(psych_profile__icontains=query))
        personnel_results = Personnel.objects.filter(personnel_query)
        for item in personnel_results:
            results.append({
                'type': 'personnel',
                'name': item.name,
                'description': item.biography,
                'url': request.build_absolute_uri(reverse('DZ_personnel', kwargs={'slug': item.slug})),
            })

    return Response(results)


@api_view(['GET'])
def classifications(request):
    return Response(
        {
            'threat_classes': {
                'Класс "Афина" (Безопасный)': 'Объект полностью изучен, его свойства предсказуемы и не представляют угрозы.',
                'Класс "Гермес" (Нейтральный)': 'Объект обладает аномальными свойствами, но не проявляет враждебности.',
                'Класс "Гефест" (Средняя угроза)': 'Объект пассивно опасен из-за своих свойств (например, радиация), но не является активно враждебным.',
                'Класс "Прометей" (Высокая угроза)': 'Разумный и активно враждебный объект, который целенаправленно стремится нарушить условия содержания.',
                'Класс "Аид" (Высшая угроза)': 'Объект, чья природа плохо изучена и который обладает потенциалом к событию класса K (конец света).'
            },
            'personnel_classes': {
                'lower_and_civil_classes': {
                    'Класс A': 'Расходный персонал для опасных задач.',
                    'Класс B': 'Сотрудники собственной полицейской службы.',
                    'Класс C': 'Группы быстрого реагирования из гражданских (не работают с аномалиями).',
                    'Класс D': 'Сотрудники разведки (не работают с аномалиями).',
                    'Класс E ("Затирщики")': 'Отдел информационной безопасности.'
                },
                'scientific_and_operational_staff': {
                    'Классы F, G, H': 'Младшие, обычные и старшие научные сотрудники.',
                    'Класс I (ГБР)': 'Основные ударные отряды для задержания аномалий.',
                    'Классы J, K': 'Охрана периметра Зон и внутренняя охрана.',
                    'Класс L': 'Полевые агенты.',
                    'Класс N': 'Аномальные сотрудники, работающие на организацию.'
                },
                'command_staff_and_senior_management': {
                    'Классы M-W': 'Различные советы, командиры и директора, управляющие организацией на разных уровнях.',
                    'Класс X': 'Высший совет безопасности, личная охрана Z-1 и Z-2.',
                    'Класс Y ("Наследие")': 'Сверхсекретный протокол "Последнего Дня".',
                    'Класс Z-1 (Высший совет)': 'Управляет всей организацией (9 членов).',
                    'Класс Z-2 (Основатель)': 'Высшая инстанция (1 человек).'
                }
            }
        }
    )
