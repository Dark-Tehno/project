from django.contrib import admin
from .models import Participant, Music, Album, Concert, Merch, News

# Register your models here.

admin.site.register(Participant)
admin.site.register(Music)
admin.site.register(Album)
admin.site.register(Concert)
admin.site.register(Merch)
admin.site.register(News)