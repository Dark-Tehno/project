"""API для плагина/мода на сервере Minecraft.

Авторизация: заголовок  X-Server-Key: <WEWECRAFT_SERVER_KEY из settings.py>
"""
import hmac
import uuid as uuidlib

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import LinkCode, LinkError, MinecraftProfile


class HasServerKey(BasePermission):
    def has_permission(self, request, view):
        expected = getattr(settings, "WEWECRAFT_SERVER_KEY", "")
        given = request.headers.get("X-Server-Key", "")
        return bool(expected) and hmac.compare_digest(expected, given)


class ServerThrottle(AnonRateThrottle):
    rate = "60/minute"


class LinkConfirmAPIView(APIView):
    """POST {code, uuid, username} — игрок ввёл /link КОД в игре."""

    permission_classes = [HasServerKey]
    authentication_classes = []
    throttle_classes = [ServerThrottle]

    def post(self, request):
        code = request.data.get("code", "")
        username = str(request.data.get("username", ""))[:16]
        try:
            mc_uuid = uuidlib.UUID(str(request.data.get("uuid", "")))
        except ValueError:
            return Response({"ok": False, "error": "Некорректный UUID."}, status=400)

        try:
            profile = LinkCode.consume(code, mc_uuid, username)
        except LinkError as exc:
            return Response({"ok": False, "error": str(exc)}, status=400)

        return Response({"ok": True, "site_username": profile.user.username})


class PlayerInfoAPIView(APIView):
    """GET /api/player/<uuid>/ — привязан ли игрок и к какому аккаунту сайта."""

    permission_classes = [HasServerKey]
    authentication_classes = []
    throttle_classes = [ServerThrottle]

    def get(self, request, player_uuid):
        profile = (
            MinecraftProfile.objects.select_related("user").filter(uuid=player_uuid).first()
        )
        if profile is None:
            return Response({"linked": False})

        username = request.query_params.get("username")
        if username and username != profile.username:
            profile.username = username[:16]
            profile.save(update_fields=["username"])

        return Response({"linked": True, "site_username": profile.user.username})
