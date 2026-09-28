import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from .models import TwoFactorCode


TWO_FACTOR_CODE_TTL_MINUTES = 10
FROM_EMAIL = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@vsp210.ru")


def generate_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_two_factor_code(user):
    code = generate_code()
    entry = TwoFactorCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=TWO_FACTOR_CODE_TTL_MINUTES),
    )
    send_code_email(
        user.email,
        subject="Код входа — Dark.Account",
        code=code,
        heading="Подтвердите вход",
        intro=(
            "Кто-то (надеемся, что это вы) пытается войти в ваш аккаунт Dark.Account. "
            "Введите этот код, чтобы продолжить."
        ),
        ttl_text=f"Код действует {TWO_FACTOR_CODE_TTL_MINUTES} минут.",
    )
    return entry


def send_code_email(email, subject, code, heading, intro, ttl_text):
    if not email:
        return

    context = {
        "subject": subject,
        "heading": heading,
        "intro": intro,
        "code": code,
        "ttl_text": ttl_text,
        "year": timezone.now().year,
    }
    html_body = render_to_string("account/email/code_email.html", context)
    text_body = strip_tags(
        f"{heading}\n\n{intro}\n\nВаш код: {code}\n\n{ttl_text}\n\n"
        "Если вы не запрашивали это действие, просто проигнорируйте письмо."
    )

    message = EmailMultiAlternatives(subject, text_body, FROM_EMAIL, [email])
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=True)