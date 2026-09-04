from django.contrib import admin
from .models import *

# Register your models here.
@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'status', 'commander_name')
    list_filter = ('status',)
    search_fields = ('name', 'location', 'description', 'specialization')
    prepopulated_fields = {'slug': ('name',)}

    def commander_name(self, obj):
        return obj.commander.name if obj.commander else "Нет"
    commander_name.short_description = "Командир Зоны"

@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ('get_full_id', 'name', 'threat_class', 'containment_zone')
    list_filter = ('threat_class', 'containment_zone')
    search_fields = ('name', 'description', 'anomalous_properties')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ('name', 'callsign', 'personnel_class', 'position', 'status')
    list_filter = ('personnel_class', 'status', 'position')
    search_fields = ('name', 'callsign', 'position', 'biography', 'psych_profile')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'anomaly')
    list_filter = ('date', 'anomaly')
    search_fields = ('name', 'description', 'consequences')

@admin.register(InterrogationProtocol)
class InterrogationProtocolAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'anomaly', 'interrogator', 'interrogated_person')
    list_filter = ('date', 'anomaly', 'interrogator')
    search_fields = ('name', 'dialogue', 'interrogator', 'interrogated_person')

@admin.register(NotClassifiedMaterial)
class NotClassifiedMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'anomaly')
    list_filter = ('date', 'anomaly')
    search_fields = ('name', 'data')
    prepopulated_fields = {'slug': ('name',)}