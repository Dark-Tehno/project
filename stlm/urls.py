from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='stlm_index'),
    path('about/', views.about, name='stlm_about'),
    path('albums/', views.albums, name='stlm_albums'),
    path('music/album/<int:album_id>/', views.album_detail, name='stlm_album_detail'),
    path('music/track/<int:track_id>/', views.track_detail, name='stlm_track_detail'),
    path('tour/', views.tour, name='stlm_tour'),
    path('merch/', views.merch, name='stlm_merch'),
    # path('news/', views.news, name='stlm_news'),
]