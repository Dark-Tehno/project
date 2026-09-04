from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='dark_news_index'),
]