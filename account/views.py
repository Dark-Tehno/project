import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CodeConfirmForm,
    LoginForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ProfileEditForm,
    RegisterForm,
)
from .models import (
    DarkAccount,
    Device,
    EmailConfirmation,
    LoginHistory,
    PasswordReset,
    Token,
    Version,
)

DEVICE_COOKIE_NAME = "dtd_id"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 2  # 2 года
FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@dark.talk")


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "0.0.0.0"


def parse_user_agent(ua):
    ua_l = (ua or "").lower()

    if "edg/" in ua_l:
        browser = "Edge"
    elif "opr/" in ua_l or "opera" in ua_l:
        browser = "Opera"
    elif "chrome" in ua_l and "chromium" not in ua_l:
        browser = "Chrome"
    elif "firefox" in ua_l:
        browser = "Firefox"
    elif "safari" in ua_l:
        browser = "Safari"
    else:
        browser = "Неизвестный браузер"

    if "windows" in ua_l:
        os_name = "Windows"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os_name = "macOS"
    elif "android" in ua_l:
        os_name = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l or "ios" in ua_l:
        os_name = "iOS"
    elif "linux" in ua_l:
        os_name = "Linux"
    else:
        os_name = "Неизвестная ОС"

    if "ipad" in ua_l or "tablet" in ua_l:
        device_type = Device.DeviceType.TABLET
    elif "mobile" in ua_l:
        device_type = Device.DeviceType.MOBILE
    elif "bot" in ua_l or "spider" in ua_l or "crawler" in ua_l:
        device_type = Device.DeviceType.BOT
    elif ua_l:
        device_type = Device.DeviceType.DESKTOP
    else:
        device_type = Device.DeviceType.UNKNOWN

    return browser, os_name, device_type


def get_or_create_device(request, user):
    """Находит устройство по куке dtd_id или создаёт новое."""
    ip = get_client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")
    browser, os_name, device_type = parse_user_agent(ua)

    device_id = request.COOKIES.get(DEVICE_COOKIE_NAME)
    is_new_cookie = False
    if not device_id:
        device_id = uuid.uuid4().hex
        is_new_cookie = True

    device, created = Device.objects.get_or_create(
        user=user,
        device_id=device_id,
        defaults={
            "name": f"{browser} · {os_name}",
            "device_type": device_type,
            "operating_system": os_name,
            "browser": browser,
            "user_agent": ua,
            "first_ip": ip,
            "last_ip": ip,
        },
    )
    if not created:
        device.last_ip = ip
        device.user_agent = ua
        device.browser = browser
        device.operating_system = os_name
        device.device_type = device_type
        device.save()

    return device, device_id, is_new_cookie


def generate_code():
    return f"{random.randint(0, 999999):06d}"


def send_code_email(email, subject, code):
    if not email:
        return
    send_mail(
        subject,
        f"Ваш код: {code}\n\nЕсли вы не запрашивали это действие, просто проигнорируйте письмо.",
        FROM_EMAIL,
        [email],
        fail_silently=True,
    )


# ---------------------------------------------------------------------------
# Регистрация / вход / выход
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect("profile-view")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()

        code = generate_code()
        EmailConfirmation.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        send_code_email(user.email, "Подтверждение почты — Dark.Talk", code)

        login(request, user)
        device, device_id, is_new_cookie = get_or_create_device(request, user)
        LoginHistory.objects.create(
            user=user,
            device=device,
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            status=LoginHistory.Status.SUCCESS,
            reason="Регистрация",
        )

        messages.success(
            request,
            "Аккаунт создан. Мы отправили код подтверждения на вашу почту.",
        )
        response = redirect("email-confirm")
        if is_new_cookie:
            response.set_cookie(
                DEVICE_COOKIE_NAME, device_id,
                max_age=DEVICE_COOKIE_MAX_AGE, httponly=True, samesite="Lax",
            )
        return response

    return render(request, "account/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("profile-view")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")

        user = authenticate(request, username=username, password=password)

        if user is None:
            candidate = DarkAccount.objects.filter(username=username).first()
            if candidate:
                LoginHistory.objects.create(
                    user=candidate, ip=ip, user_agent=ua,
                    status=LoginHistory.Status.FAILED,
                    reason="Неверный логин или пароль",
                )
            form.add_error(None, "Неверное имя пользователя или пароль.")
        else:
            existing_device_id = request.COOKIES.get(DEVICE_COOKIE_NAME)
            existing_device = None
            if existing_device_id:
                existing_device = Device.objects.filter(
                    user=user, device_id=existing_device_id
                ).first()

            if existing_device and existing_device.blocked:
                LoginHistory.objects.create(
                    user=user, device=existing_device, ip=ip, user_agent=ua,
                    status=LoginHistory.Status.BLOCKED,
                    reason="Устройство заблокировано пользователем",
                )
                form.add_error(
                    None,
                    "Это устройство заблокировано. Войдите с другого устройства, "
                    "чтобы снять блокировку.",
                )
            else:
                login(request, user)
                device, device_id, is_new_cookie = get_or_create_device(request, user)
                user.is_online = True
                user.last_online = timezone.now()
                user.save(update_fields=["is_online", "last_online"])
                LoginHistory.objects.create(
                    user=user, device=device, ip=ip, user_agent=ua,
                    status=LoginHistory.Status.SUCCESS,
                )
                response = redirect("profile-view")
                if is_new_cookie:
                    response.set_cookie(
                        DEVICE_COOKIE_NAME, device_id,
                        max_age=DEVICE_COOKIE_MAX_AGE, httponly=True, samesite="Lax",
                    )
                return response

    return render(request, "account/login.html", {"form": form})


@login_required
def logout_view(request):
    if request.method == "POST":
        user = request.user
        user.is_online = False
        user.last_online = timezone.now()
        user.save(update_fields=["is_online", "last_online"])
        logout(request)
        messages.info(request, "Вы вышли из аккаунта.")
        return redirect("login-view")

    return render(request, "account/logout.html")


# ---------------------------------------------------------------------------
# Профиль
# ---------------------------------------------------------------------------

@login_required
def profile_view(request):
    user = request.user

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль обновлён.")
            return redirect("profile-view")
    else:
        form = ProfileEditForm(instance=user)

    context = {
        "form": form,
        "devices_count": Device.objects.filter(user=user).count(),
        "tokens_count": Token.objects.filter(device__user=user).count(),
        "active_nav": "profile",
    }
    return render(request, "account/profile.html", context)


@login_required
def security_view(request):
    context = {
        "active_nav": "security",
        "last_confirmation": EmailConfirmation.objects.filter(user=request.user)
        .order_by("-created_at")
        .first(),
    }
    return render(request, "account/security.html", context)


@login_required
def toggle_two_factor(request):
    if request.method == "POST":
        user = request.user
        user.two_factor_enabled = not user.two_factor_enabled
        user.save(update_fields=["two_factor_enabled"])
        if user.two_factor_enabled:
            messages.success(request, "Двухфакторная аутентификация включена.")
        else:
            messages.info(request, "Двухфакторная аутентификация выключена.")
    return redirect("security-view")


# ---------------------------------------------------------------------------
# Устройства
# ---------------------------------------------------------------------------

@login_required
def devices_view(request):
    devices = Device.objects.filter(user=request.user)
    context = {
        "devices": devices,
        "current_device_id": request.COOKIES.get(DEVICE_COOKIE_NAME),
        "active_nav": "devices",
    }
    return render(request, "account/devices.html", context)


@login_required
def device_toggle_trust(request, device_id):
    device = get_object_or_404(Device, id=device_id, user=request.user)
    if request.method == "POST":
        device.trusted = not device.trusted
        device.save(update_fields=["trusted"])
        messages.success(request, "Статус доверенного устройства обновлён.")
    return redirect("devices-view")


@login_required
def device_toggle_block(request, device_id):
    device = get_object_or_404(Device, id=device_id, user=request.user)
    current_device_id = request.COOKIES.get(DEVICE_COOKIE_NAME)
    if request.method == "POST":
        if device.device_id == current_device_id and not device.blocked:
            messages.error(request, "Нельзя заблокировать устройство, с которого вы сейчас работаете.")
        else:
            device.blocked = not device.blocked
            device.save(update_fields=["blocked"])
            messages.success(request, "Статус блокировки устройства обновлён.")
    return redirect("devices-view")


@login_required
def device_delete(request, device_id):
    device = get_object_or_404(Device, id=device_id, user=request.user)
    current_device_id = request.COOKIES.get(DEVICE_COOKIE_NAME)
    if request.method == "POST":
        is_current = device.device_id == current_device_id
        device.delete()
        messages.success(request, "Устройство удалено.")
        if is_current:
            logout(request)
            return redirect("login-view")
    return redirect("devices-view")


# ---------------------------------------------------------------------------
# История входов
# ---------------------------------------------------------------------------

@login_required
def login_history_view(request):
    history = (
        LoginHistory.objects.filter(user=request.user)
        .select_related("device")
        .order_by("-created_at")[:200]
    )
    context = {"login_history": history, "active_nav": "history"}
    return render(request, "account/login_history.html", context)


# ---------------------------------------------------------------------------
# Подтверждение почты
# ---------------------------------------------------------------------------

@login_required
def email_confirm_view(request):
    user = request.user
    if user.email_confirmed:
        messages.info(request, "Почта уже подтверждена.")
        return redirect("security-view")

    form = CodeConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"].strip()
        confirmation = (
            EmailConfirmation.objects.filter(user=user, code=code, confirmed=False)
            .order_by("-created_at")
            .first()
        )
        if confirmation and confirmation.expires_at >= timezone.now():
            confirmation.confirmed = True
            confirmation.confirmed_at = timezone.now()
            confirmation.save()
            user.email_confirmed = True
            user.save(update_fields=["email_confirmed"])
            messages.success(request, "Почта успешно подтверждена.")
            return redirect("security-view")
        form.add_error("code", "Неверный или истёкший код.")

    return render(request, "account/email_confirm.html", {"form": form})


@login_required
def email_confirm_resend(request):
    user = request.user
    if request.method == "POST" and not user.email_confirmed and user.email:
        code = generate_code()
        EmailConfirmation.objects.create(
            user=user, code=code, expires_at=timezone.now() + timedelta(hours=24)
        )
        send_code_email(user.email, "Подтверждение почты — Dark.Talk", code)
        messages.success(request, "Новый код отправлен на почту.")
    return redirect("email-confirm")


# ---------------------------------------------------------------------------
# Сброс пароля
# ---------------------------------------------------------------------------

def password_reset_request_view(request):
    if request.user.is_authenticated:
        return redirect("profile-view")

    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = DarkAccount.objects.filter(email=email).first()
        if user:
            code = generate_code()
            PasswordReset.objects.create(
                user=user, code=code, expires_at=timezone.now() + timedelta(minutes=30)
            )
            send_code_email(email, "Восстановление пароля — Dark.Talk", code)
        messages.success(
            request,
            "Если аккаунт с такой почтой существует, мы отправили код для сброса пароля.",
        )
        return redirect("password-reset-confirm")

    return render(request, "account/password_reset_request.html", {"form": form})


def password_reset_confirm_view(request):
    if request.user.is_authenticated:
        return redirect("profile-view")

    form = PasswordResetConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        code = form.cleaned_data["code"].strip()
        new_password = form.cleaned_data["new_password1"]

        user = DarkAccount.objects.filter(email=email).first()
        reset = None
        if user:
            reset = (
                PasswordReset.objects.filter(user=user, code=code, used=False)
                .order_by("-created_at")
                .first()
            )

        if reset and reset.expires_at >= timezone.now():
            user.set_password(new_password)
            user.save()
            reset.used = True
            reset.used_at = timezone.now()
            reset.save()
            messages.success(request, "Пароль изменён. Теперь вы можете войти.")
            return redirect("login-view")

        form.add_error(None, "Неверная почта, код или срок его действия истёк.")

    return render(request, "account/password_reset_confirm.html", {"form": form})
