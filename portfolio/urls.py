from django.urls import path
from django.views.generic import TemplateView
from .views import *

urlpatterns = [
    path('', portfolio, name='portfolio'),
    path('portal/', portal, name='portal'),
    path('dark-lang/', darklang, name='darklang'),
    path('birthday/<str:name>/<str:date>', birthday, name='birthday'),
    
    path('favicon.ico', favicon, name='favicon'),
    path('logo.svg', logo, name='logo'),
    path('robots.txt', robots, name='robots'),
]
