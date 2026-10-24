from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.index, name="wewecraft-index"),
    path("join/", views.how_to_join, name="wewecraft-join"),
    path("rules/", views.rules, name="wewecraft-rules"),
    path("news/", views.news, name="wewecraft-news"),
    path("players/", views.players, name="wewecraft-players"),
    path("online.json", views.online_json, name="wewecraft-online"),

    path("link/", views.link_view, name="wewecraft-link"),
    path("link/generate/", views.link_generate, name="wewecraft-link-generate"),
    path("link/unlink/", views.link_unlink, name="wewecraft-link-unlink"),

    # API для сервера Minecraft
    path("api/link/", api.LinkConfirmAPIView.as_view(), name="wewecraft-api-link"),
    path("api/player/<uuid:player_uuid>/", api.PlayerInfoAPIView.as_view(), name="wewecraft-api-player"),
]
