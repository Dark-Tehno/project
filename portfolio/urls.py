from django.urls import path
from .views import *

urlpatterns = [
    path('', portfolio, name='portfolio'),
    path('dark-lang/', darklang, name='darklang'),
    path('birthday/<str:name>/<str:date>', birthday, name='birthday'),
    
    path('favicon.ico', favicon, name='favicon'),
    path('robots.txt', robots, name='robots'),
]
