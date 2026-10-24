from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.http import JsonResponse

from .models import LinkCode, LinkError, MinecraftProfile, News, Rule
from .server_status import get_online_players


def server_context():
    return {
        "server_name": getattr(settings, "WEWECRAFT_SERVER_NAME", "WeWeCraft"),
        "server_address": getattr(settings, "WEWECRAFT_SERVER_ADDRESS", "play.wewecraft.ru"),
        "server_version": getattr(settings, "WEWECRAFT_SERVER_VERSION", "1.21"),
    }


def index(request):
    ctx = server_context()
    ctx.update(
        news=News.objects.filter(published=True)[:3],
        players_count=MinecraftProfile.objects.count(),
        active_nav="home",
    )
    return render(request, "wewecraft/index.html", ctx)


def how_to_join(request):
    ctx = server_context()
    ctx["active_nav"] = "join"
    return render(request, "wewecraft/join.html", ctx)


def rules(request):
    ctx = server_context()
    ctx.update(rules=Rule.objects.all(), active_nav="rules")
    return render(request, "wewecraft/rules.html", ctx)


def news(request):
    ctx = server_context()
    ctx.update(news=News.objects.filter(published=True), active_nav="news")
    return render(request, "wewecraft/news.html", ctx)


def players(request):
    ctx = server_context()
    ctx.update(
        profiles=MinecraftProfile.objects.select_related("user").order_by("-linked_at"),
        online=get_online_players(),
        active_nav="players",
    )
    return render(request, "wewecraft/players.html", ctx)


@login_required
def link_view(request):
    """Страница привязки: статус и (если нужно) активный код."""
    profile = MinecraftProfile.objects.filter(user=request.user).first()
    link = None
    if profile is None:
        link = (
            LinkCode.objects.filter(user=request.user, used=False, expires_at__gt=timezone.now())
            .order_by("-created_at")
            .first()
        )
    ctx = server_context()
    ctx.update(profile=profile, link=link, active_nav="link")
    return render(request, "wewecraft/link.html", ctx)


@login_required
@require_POST
def link_generate(request):
    try:
        LinkCode.generate_for(request.user)
    except LinkError as exc:
        messages.error(request, str(exc))
    return redirect("wewecraft-link")


@login_required
@require_POST
def link_unlink(request):
    deleted, _ = MinecraftProfile.objects.filter(user=request.user).delete()
    if deleted:
        messages.success(request, "Игровой аккаунт отвязан.")
    return redirect("wewecraft-link")


def online_json(request):
    """Публичный JSON для автообновления списка «сейчас на сервере»."""
    return JsonResponse(get_online_players())
