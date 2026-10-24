import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

# Алфавит без похожих символов (0/O, 1/I/L), чтобы код было легко вводить в игре
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_TTL = timedelta(minutes=10)


class LinkError(Exception):
    """Ошибка привязки (неверный/просроченный код, аккаунт уже привязан)."""


class MinecraftProfile(models.Model):
    """Игровой аккаунт, привязанный к аккаунту на сайте.

    OneToOne в обе стороны: один аккаунт сайта = один игровой аккаунт.
    Главный идентификатор — UUID, а не ник (ник в Minecraft можно сменить).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="minecraft",
        verbose_name="Аккаунт на сайте",
    )
    uuid = models.UUIDField("Minecraft UUID", unique=True)
    username = models.CharField("Игровой ник", max_length=16)
    linked_at = models.DateTimeField("Привязан", auto_now_add=True)

    class Meta:
        verbose_name = "Игровой аккаунт"
        verbose_name_plural = "Игровые аккаунты"

    def __str__(self):
        return f"{self.username} ({self.user})"


class LinkCode(models.Model):
    """Одноразовый код привязки: создаётся на сайте, вводится в игре (/link КОД)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="minecraft_link_codes",
        verbose_name="Аккаунт на сайте",
    )
    code = models.CharField("Код", max_length=16, unique=True, db_index=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    expires_at = models.DateTimeField("Действует до")
    used = models.BooleanField("Использован", default=False)
    used_at = models.DateTimeField("Использован в", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Код привязки"
        verbose_name_plural = "Коды привязки"

    def __str__(self):
        return f"{self.code} → {self.user}"

    @property
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

    # ---------- создание кода (вызывается из view на сайте) ----------
    @classmethod
    def generate_for(cls, user):
        """Создаёт новый код для пользователя; старые неиспользованные гасит."""
        if MinecraftProfile.objects.filter(user=user).exists():
            raise LinkError("Игровой аккаунт уже привязан.")

        with transaction.atomic():
            cls.objects.filter(user=user, used=False).update(used=True)
            while True:
                code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
                if not cls.objects.filter(code=code).exists():
                    break
            return cls.objects.create(
                user=user,
                code=code,
                expires_at=timezone.now() + CODE_TTL,
            )

    # ---------- использование кода (вызывается из API для плагина сервера) ----------
    @classmethod
    def consume(cls, code, mc_uuid, mc_username):
        """Проверяет код и создаёт MinecraftProfile. Возвращает профиль."""
        code = (code or "").strip().upper()

        with transaction.atomic():
            # select_for_update защищает от двойного использования кода при гонке запросов
            link = (
                cls.objects.select_for_update()
                .select_related("user")
                .filter(code=code)
                .first()
            )
            if link is None or not link.is_valid:
                raise LinkError("Неверный или просроченный код.")

            if MinecraftProfile.objects.filter(uuid=mc_uuid).exists():
                raise LinkError("Этот игровой аккаунт уже привязан к другому профилю.")
            if MinecraftProfile.objects.filter(user=link.user).exists():
                raise LinkError("К аккаунту на сайте уже привязан игрок.")

            link.used = True
            link.used_at = timezone.now()
            link.save(update_fields=["used", "used_at"])

            return MinecraftProfile.objects.create(
                user=link.user,
                uuid=mc_uuid,
                username=mc_username,
            )


class Rule(models.Model):
    """Пункт правил сервера (редактируется в админке)."""

    number = models.PositiveSmallIntegerField("Порядок", default=1)
    title = models.CharField("Заголовок", max_length=120)
    text = models.TextField("Описание")
    punishment = models.CharField("Наказание", max_length=200, blank=True)

    class Meta:
        ordering = ["number"]
        verbose_name = "Правило"
        verbose_name_plural = "Правила"

    def __str__(self):
        return f"{self.number}. {self.title}"


class News(models.Model):
    """Новость сервера."""

    title = models.CharField("Заголовок", max_length=160)
    text = models.TextField("Текст")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wewecraft_news",
        verbose_name="Автор",
    )
    published = models.BooleanField("Опубликована", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость"
        verbose_name_plural = "Новости"

    def __str__(self):
        return self.title
