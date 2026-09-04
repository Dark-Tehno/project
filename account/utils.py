"""
Автоматическое определение устройства из запроса.

Требуются пакеты:
    pip install user-agents django-ipware

user-agents  -> разбор User-Agent (ОС, браузер, тип устройства)
django-ipware -> корректное определение реального IP клиента за прокси/балансировщиками
(если не установлен django-ipware — используется fallback на X-Forwarded-For / REMOTE_ADDR)
"""

import uuid
from django.contrib.gis.geoip2 import GeoIP2
from django.utils import timezone
from rest_framework.permissions import BasePermission
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

try:
    from user_agents import parse as parse_user_agent
except ImportError: 
    parse_user_agent = None

try:
    from ipware import get_client_ip
except ImportError: 
    get_client_ip = None

from .models import Device, Token


def get_client_ip_address(request):
    """Реальный IP клиента с учётом прокси, либо fallback."""
    if get_client_ip:
        ip, _is_routable = get_client_ip(request)
        if ip:
            return ip
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def get_geo_by_ip(ip):
    """
    Страна / город / часовой пояс по IP.
    """
    try:
        g = GeoIP2()
        data = g.city(ip)
        return data.get('country_name') or '', data.get('city') or '', ''
    except Exception:
        return '', '', ''


def parse_device_info(request):
    """Разбор User-Agent: ОС, браузер, тип устройства, читаемое имя."""
    ua_string = request.META.get('HTTP_USER_AGENT', '')

    info = {
        'operating_system': '',
        'system_version': '',
        'browser': '',
        'browser_version': '',
        'device_type': Device.DeviceType.UNKNOWN,
        'name': 'Неизвестное устройство',
    }

    if parse_user_agent and ua_string:
        ua = parse_user_agent(ua_string)

        info['operating_system'] = ua.os.family or ''
        info['system_version'] = ua.os.version_string or ''
        info['browser'] = ua.browser.family or ''
        info['browser_version'] = ua.browser.version_string or ''

        if ua.is_mobile:
            info['device_type'] = Device.DeviceType.MOBILE
        elif ua.is_tablet:
            info['device_type'] = Device.DeviceType.TABLET
        elif ua.is_pc:
            info['device_type'] = Device.DeviceType.DESKTOP
        elif ua.is_bot:
            info['device_type'] = Device.DeviceType.BOT

        device_name = ua.device.family
        if device_name and device_name != 'Other':
            info['name'] = device_name
        elif info['operating_system']:
            info['name'] = f"{info['operating_system']} устройство"

    return info


def get_or_create_device(request, user, extra_data=None):
    """
    Главная точка автоматизации.

    Вызывается при регистрации и при логине. Находит устройство по
    device_id (если клиент передал свой — например, мобильное приложение
    хранит его локально), либо создаёт новое, заполняя ВСЕ поля модели
    Device автоматически из запроса.

    extra_data — необязательный dict с полями, которые клиент может
    уточнить сам (device_id, fingerprint, application, timezone и т.п.).
    Всё, что не передано явно, определяется сервером самостоятельно.
    """
    extra_data = extra_data or {}

    ip = get_client_ip_address(request)
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    parsed = parse_device_info(request)
    country, city, tz = get_geo_by_ip(ip)

    device_id = (
        extra_data.get('device_id')
        or request.META.get('HTTP_X_DEVICE_ID')
        or str(uuid.uuid4())
    )

    defaults = {
        'name': extra_data.get('name') or parsed['name'],
        'device_type': extra_data.get('device_type') or parsed['device_type'],
        'operating_system': extra_data.get('operating_system') or parsed['operating_system'],
        'system_version': extra_data.get('system_version') or parsed['system_version'],
        'browser': parsed['browser'],
        'browser_version': parsed['browser_version'],
        'application': extra_data.get('application', ''),
        'application_version': extra_data.get('application_version', ''),
        'fingerprint': extra_data.get('fingerprint', ''),
        'user_agent': ua_string,
        'first_ip': ip,
        'last_ip': ip,
        'country': country,
        'city': city,
        'timezone': extra_data.get('timezone') or tz,
        'last_seen': timezone.now(),
    }

    device, created = Device.objects.get_or_create(
        user=user,
        device_id=device_id,
        defaults=defaults,
    )

    if not created:
        for field, value in defaults.items():
            if field == 'first_ip':
                continue 
            if value not in (None, ''):
                setattr(device, field, value)
        device.save()

    return device


class DeviceTokenAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        auth = request.headers.get("Authorization")

        if not auth:
            return None

        if not auth.startswith(f"{self.keyword} "):
            return None

        key = auth.split(" ", 1)[1]

        token = Token.objects.select_related("device__user").filter(key=key).first()

        if token is None:
            raise AuthenticationFailed("Invalid token")

        return (token.device.user, token)


class StandartAPIPermission(BasePermission):

    def has_permission(self, request, view):
        secret = request.headers.get("DARK-TALK-SECRET-KEY")

        if not secret:
            return False

        parts = secret.split("--")
        key = parts[0]
        version = parts[1] if len(parts) > 1 else "unofficial|0.0.0"

        if key != settings.DARK_TALK_SECRET_KEY:
            return False

        request.app_version = version

        return True