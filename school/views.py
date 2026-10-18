"""API подготовки к заданиям 4 (ударения) и 5 (паронимы) ЕГЭ по русскому языку.

Настройка GigaChat — через Django settings или переменные окружения:
  GIGACHAT_CREDENTIALS  — ключ авторизации (обязательно для ИИ-функций)
  GIGACHAT_MODEL        — модель (по умолчанию GigaChat-3-Ultra)
  GIGACHAT_SCOPE        — scope (по умолчанию GIGACHAT_API_PERS)
  GIGACHAT_BASE_URL     — адрес API (по умолчанию https://api.giga.chat/v1)
  GIGACHAT_VERIFY_SSL   — 1/0, проверять ли TLS-сертификат (по умолчанию 0)

Тесты по умолчанию берутся из проверенного банка (bank.py) и не требуют ИИ.
ИИ используется для генерации по запросу (?source=ai) и для разбора ответов (POST).
"""
import os
from functools import lru_cache

from django.conf import settings
from django.shortcuts import render
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from . import generators

AI_ATTEMPTS = 2
MAX_ITEMS = 10


class AIUnavailable(Exception):
    """GigaChat не настроен."""


class SchoolThrottle(UserRateThrottle):
    scope = "school"
    rate = "60/min"


def _setting(name, default=""):
    value = getattr(settings, name, None)
    if value in (None, ""):
        value = os.environ.get(name, default)
    return value


@lru_cache(maxsize=1)
def _client():
    credentials = _setting("GIGACHAT_CREDENTIALS", "YWQ1MDYxMjIt0TFmOC00NmNhLWFiNWYtYWRmN2M1YjFmODM5OjQzMWMzYTU4LWZiMGYtNGY3NS1iMWMwLWUwNWVmMTExMDkxOA==")
    if not credentials:
        raise AIUnavailable("GigaChat не настроен: задайте GIGACHAT_CREDENTIALS.")
    verify = str(_setting("GIGACHAT_VERIFY_SSL", "0")).lower() in ("1", "true", "yes")
    return GigaChat(
        base_url=_setting("GIGACHAT_BASE_URL", "https://api.giga.chat/v1"),
        credentials=credentials,
        scope=_setting("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        verify_ssl_certs=verify,
        timeout=45,
    )


def _ask(system, user="Выполни задание.", temperature=0.7):
    chat = Chat(
        model=_setting("GIGACHAT_MODEL", "GigaChat-3-Ultra"),
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=system),
            Messages(role=MessagesRole.USER, content=user),
        ],
        temperature=temperature,
    )
    return _client().chat(chat).choices[0].message.content


def _generate_with_ai(prompt, validator):
    """Просит ИИ составить задание и проверяет результат. None — если не вышло."""
    for attempt in range(AI_ATTEMPTS):
        try:
            return validator(generators.extract_json(_ask(prompt)))
        except AIUnavailable:
            return None
    return None


def _clean_list(value, max_len):
    """Список непустых строк ограниченной длины или None."""
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        return None
    result = [v.strip() for v in value if isinstance(v, str) and v.strip()]
    if len(result) != len(value) or any(len(v) > max_len for v in result):
        return None
    return result


def _numbered(lines):
    return "\n".join("%d. %s" % (i, line) for i, line in enumerate(lines, 1))


def _ai_error_response(exc):
    if isinstance(exc, AIUnavailable):
        return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"error": "ИИ сейчас недоступен. Попробуйте позже."},
                    status=status.HTTP_502_BAD_GATEWAY)


class SchoolBaseView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SchoolThrottle]


class SchoolAPIStressMarksView(SchoolBaseView):
    def get(self, request):
        """Тест на ударения. ?source=ai — составить тест с помощью ИИ."""
        source, fallback, items = "bank", False, None
        if request.query_params.get("source") == "ai":
            items = _generate_with_ai(generators.stress_generation_prompt(), generators.validate_ai_stress)
            if items:
                source = "ai"
            else:
                fallback = True
        if not items:
            items = generators.make_stress_items()
        payload = {
            "test": generators.stress_items_to_text(items),
            "task": generators.STRESS_TASK,
            "items": items,
            "source": source,
        }
        if fallback:
            payload["fallback"] = True
        return Response(payload)

    def post(self, request):
        """Разбор слов с отмеченными ударениями."""
        words = _clean_list(request.data.get("words"), 60)
        if not words:
            return Response({"error": "No words provided"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            text = _ask(generators.STRESS_CHECK_PROMPT, _numbered(words), temperature=0.2)
        except Exception as exc:
            return _ai_error_response(exc)
        return Response({"result": text})


class SchoolAPIParonymsView(SchoolBaseView):
    def get(self, request):
        """Задание на паронимы. ?source=ai — составить задание с помощью ИИ."""
        source, fallback, items = "bank", False, None
        if request.query_params.get("source") == "ai":
            items = _generate_with_ai(generators.paronym_generation_prompt(), generators.validate_ai_paronyms)
            if items:
                source = "ai"
            else:
                fallback = True
        if not items:
            items = generators.make_paronym_items()
        payload = {
            "test": generators.paronym_items_to_text(items),
            "task": generators.PARONYM_TASK,
            "items": items,
            "source": source,
        }
        if fallback:
            payload["fallback"] = True
        return Response(payload)

    def post(self, request):
        """Найти неверно употреблённый пароним и объяснить."""
        sentences = _clean_list(request.data.get("sentences"), 400)
        if not sentences:
            return Response({"error": "No sentences provided"}, status=status.HTTP_400_BAD_REQUEST)
        user_prompt = generators.PARONYM_TASK + "\n\n" + _numbered(sentences)
        try:
            text = _ask(generators.PARONYM_CHECK_PROMPT, user_prompt, temperature=0.2)
        except Exception as exc:
            return _ai_error_response(exc)
        return Response({"result": text})


def index(request):
    return render(request, "school/school.html")