from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='stlm_index'),
    path('about/', views.about, name='stlm_about'),
    path('albums/', views.albums, name='stlm_albums'),
    path('tour/', views.tour, name='stlm_tour'),
    path('merch/', views.merch, name='stlm_merch'),
    path('news/', views.news, name='stlm_news'),
]