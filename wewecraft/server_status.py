"""Запрос списка игроков у плагина на сервере Minecraft.

settings.py:
    WEWECRAFT_PLUGIN_URL   = "http://188.127.241.222:25774"
    WEWECRAFT_PLUGIN_TOKEN = "..."   # заголовок X-Token
"""
import json
import logging
import urllib.request
import uuid as uuidlib

from django.conf import settings
from django.core.cache import cache

from .models import MinecraftProfile

log = logging.getLogger(__name__)
CACHE_KEY = "wewecraft:online"
CACHE_SECONDS = 5


def _fetch_plugin():
    url = getattr(settings, "WEWECRAFT_PLUGIN_URL", "").rstrip("/")
    token = getattr(settings, "WEWECRAFT_PLUGIN_TOKEN", "")
    if not url:
        return None
    req = urllib.request.Request(f"{url}/players", headers={"X-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # сервер выключен, таймаут, неверный токен и т.д.
        log.warning("wewecraft: плагин недоступен: %s", exc)
        return None


def get_online_players():
    """Возвращает {'ok': bool, 'count': int, 'players': [...]}.

    Каждый игрок: name, uuid, linked (bool), site_username, health, max_health,
    food, level, game_mode, dimension, ping. Координаты наружу не отдаём.
    Игроки видны, даже если аккаунт на сайте не привязан (linked=False).
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    data = _fetch_plugin()
    if data is None:
        result = {"ok": False, "count": 0, "players": []}
        cache.set(CACHE_KEY, result, CACHE_SECONDS)
        return result

    raw = data.get("players", [])
    uuids = []
    for p in raw:
        try:
            uuids.append(uuidlib.UUID(str(p.get("uuid", ""))))
        except ValueError:
            pass
    linked = {
        pr.uuid: pr.user.username
        for pr in MinecraftProfile.objects.filter(uuid__in=uuids).select_related("user")
    }

    players = []
    for p in raw:
        try:
            pu = uuidlib.UUID(str(p.get("uuid", "")))
        except ValueError:
            pu = None
        players.append({
            "name": p.get("name", "?"),
            "uuid": str(pu) if pu else "",
            "linked": pu in linked,
            "site_username": linked.get(pu),
            "health": p.get("health"),
            "max_health": p.get("maxHealth"),
            "food": p.get("food"),
            "level": p.get("level"),
            "game_mode": p.get("gameMode"),
            "dimension": (p.get("dimension") or "").replace("minecraft:", ""),
            "ping": p.get("ping"),
        })

    result = {"ok": True, "count": len(players), "players": players}
    cache.set(CACHE_KEY, result, CACHE_SECONDS)
    return result
