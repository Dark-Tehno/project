from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

# --- Классы-перечисления для полей choices ---

class ThreatClassChoices(models.TextChoices):
    ATHENA = 'ATHENA', 'Афина'
    HERMES = 'HERMES', 'Гермес'
    HEPHAESTUS = 'HEPHAESTUS', 'Гефест'
    PROMETHEUS = 'PROMETHEUS', 'Прометей'
    HADES = 'HADES', 'Аид'

class PersonnelClassChoices(models.TextChoices):
    A = 'A', 'Класс A'
    B = 'B', 'Класс B'
    C = 'C', 'Класс C'
    D = 'D', 'Класс D'
    E = 'E', 'Класс E'
    F = 'F', 'Класс F'
    G = 'G', 'Класс G'
    H = 'H', 'Класс H'
    I = 'I', 'Класс I'
    J = 'J', 'Класс J'
    K = 'K', 'Класс K'
    L = 'L', 'Класс L'
    M = 'M', 'Класс M'
    N = 'N', 'Класс N'
    O = 'O', 'Класс O'
    P = 'P', 'Класс P'
    Q = 'Q', 'Класс Q'
    R = 'R', 'Класс R'
    S = 'S', 'Класс S'
    T = 'T', 'Класс T'
    U = 'U', 'Класс U'
    V = 'V', 'Класс V'
    W = 'W', 'Класс W'
    X = 'X', 'Класс X'
    Y = 'Y', 'Класс Y'
    Z1 = 'Z1', 'Класс Z-1'
    Z2 = 'Z2', 'Класс Z-2'

class PersonnelStatusChoices(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Активен'
    DECEASED = 'DECEASED', 'Погиб'
    RETIRED = 'RETIRED', 'В отставке'
    MIA = 'MIA', 'Пропал без вести'

class ZoneStatusChoices(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Функционирует'
    DECOMMISSIONED = 'DECOMMISSIONED', 'Заброшена'
    DESTROYED = 'DESTROYED', 'Уничтожена'

# --- Основные модели ---

class Zone(models.Model):
    name = models.CharField("Название зоны", max_length=255)
    location = models.CharField("Расположение", max_length=255)
    status = models.CharField("Статус", max_length=50, choices=ZoneStatusChoices.choices, default=ZoneStatusChoices.ACTIVE)
    commander = models.ForeignKey(
        "Personnel", 
        on_delete=models.SET_NULL, 
        verbose_name="Командир Зоны",
        null=True, 
        blank=True,
        related_name="commanded_zones" 
    )
    description = models.TextField("Общая информация")
    specialization = models.TextField("Специализация")
    command_staff = models.IntegerField("Командный состав", null=True, blank=True)
    scientific_staff = models.IntegerField("Научный персонал (F, G, H)", null=True, blank=True)
    security_personnel = models.IntegerField("Персонал безопасности (I, J, K)", null=True, blank=True)
    administrative_technical_staff = models.IntegerField("Административный и технический персонал", null=True, blank=True)
    class_a_personnel = models.IntegerField("Персонал класса А", null=True, blank=True)
    x = models.FloatField("Координата X")
    y = models.FloatField("Координата Y")
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)

    class Meta:
        verbose_name = "Зона"
        verbose_name_plural = "Зоны"

    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse("DZ_zone", kwargs={"slug": self.slug})


class Anomaly(models.Model):
    id_prefix = models.CharField("Префикс(например `DZ`)", max_length=50, default="DZ")
    id_number = models.PositiveIntegerField("Номер(например `1`)")
    name = models.CharField("Название", max_length=255)
    threat_class = models.CharField("Класс угрозы", max_length=50, choices=ThreatClassChoices.choices, default=ThreatClassChoices.ATHENA)
    description = models.TextField("Описание(html)", blank=True, null=True)
    anomalous_properties = models.TextField("Аномальные свойства(html)", blank=True, null=True)
    containment_zone = models.ForeignKey(
        Zone, 
        verbose_name="Зона содержания", 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    image = models.ImageField("Изображение", upload_to="anomalies/", blank=True, null=True)
    image_caption = models.CharField("Подпись к изображению", max_length=255, blank=True, null=True)
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)
    
    class Meta:
        verbose_name = "Аномалия"
        verbose_name_plural = "Аномалии"
        unique_together = ('id_prefix', 'id_number')

    def get_full_id(self):
        return f"{self.id_prefix}-{self.id_number:03}"

    def __str__(self):
        return f'{self.get_full_id()} "{self.name}"'
    
    def get_absolute_url(self):
        return reverse("DZ_object", kwargs={"slug": self.slug})

class Personnel(models.Model):
    name = models.CharField("ФИО", max_length=255)
    callsign = models.CharField("Позывной", max_length=100, blank=True, null=True)
    personnel_class = models.CharField("Класс персонала", max_length=50, choices=PersonnelClassChoices.choices)
    position = models.CharField("Должность", max_length=255)
    status = models.CharField("Статус", max_length=50, choices=PersonnelStatusChoices.choices, default=PersonnelStatusChoices.ACTIVE)
    biography = models.TextField("Биографическая справка(html)")
    psych_profile = models.TextField("Психологический портрет(html)")
    quote = models.TextField("Известная цитата", blank=True, null=True)
    service_marks = models.JSONField("Служебные отметки", default=list, blank=True)
    image = models.ImageField("Изображение", upload_to="personnel/", blank=True, null=True)
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)
    
    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        if self.callsign:
            return f'{self.name} "{self.callsign}"'
        return self.name
    
    def get_absolute_url(self):
        return reverse("DZ_personnel", kwargs={"slug": self.slug})


# --- Модели для Архива ---
class IncidentReport(models.Model):
    name = models.CharField("Название инцидента", max_length=255)
    date = models.DateTimeField("Дата инцидента", default=timezone.now)
    anomaly = models.ForeignKey(Anomaly, on_delete=models.CASCADE, verbose_name="Аномалия", related_name="incident_reports")
    description = models.TextField("Описание инцидента(html)")
    course_of_events = models.JSONField("Ход событий[список событий]", default=list)
    consequences = models.TextField("Последствия(html)")
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)


    def __str__(self):
        return f"Отчёт об инциденте {self.name}"
    
    def get_material_type(self):
        return "Отчёт об инциденте"
    
    
class InterrogationProtocol(models.Model):
    name = models.CharField("Название протокола", max_length=255)
    date = models.DateTimeField("Дата составления", default=timezone.now)
    anomaly = models.ForeignKey(Anomaly, on_delete=models.CASCADE, verbose_name="Связанный объект", related_name="interrogation_protocols")
    interrogator = models.CharField("Допрашивающий", max_length=255)
    interrogated_person = models.CharField("Допрашиваемый", max_length=255)
    dialogue = models.TextField("Диалог")
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)

    
    def __str__(self):
        return f"Протокол допроса {self.name}"
    
    def get_material_type(self):
        return "Протокол допроса"
    

class NotClassifiedMaterial(models.Model):
    name = models.CharField("Название", max_length=255)
    date = models.DateTimeField("Дата составления", default=timezone.now)
    anomaly = models.ForeignKey(Anomaly, on_delete=models.CASCADE, verbose_name="Связанный объект", related_name="not_classified_materials")
    data = models.TextField("Данные")
    slug = models.SlugField("URL", max_length=255, unique=True, db_index=True)

    def __str__(self):
        return f"Не классифицированный материал {self.name}"
    
    def get_material_type(self):
        return "Не классифицированный материал"
    