from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
import uuid
import random
import secrets


class Token(models.Model):
    key = models.CharField("Ключь", max_length=40, primary_key=True)
    device = models.OneToOneField(
        'Device', related_name='auth_token',
        on_delete=models.CASCADE, verbose_name="Устройство"
    )
    created = models.DateTimeField("Создано", auto_now_add=True)


    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
            if self._state.adding:
                kwargs['force_insert'] = True
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        return secrets.token_hex(20)

    def __str__(self):
        return self.key


def random_default_avatar():
    return f"defaults/default_user_photo_{random.randint(1, 3)}.png"


def avatar_path(instance, filename):
    return f"avatars/{instance.username}/{filename}"


class Version(models.Model): 
    class ApplicationType(models.TextChoices):
        WINDOWS = "windows", "Dark.Talk Windows"
        LINUX = "linux", "Dark.Talk Linux"
        MACOS = "macos", "Dark.Talk macOS"

        ANDROID = "android", "Dark.Talk Android"
        IOS = "ios", "Dark.Talk iOS"

        WEB = "web", "Dark.Talk Web"

        UNOFFICIAL = "unofficial", "Неизвестное приложение"

    application = models.CharField(choices=ApplicationType.choices, default=ApplicationType.UNOFFICIAL, verbose_name='Тип приложения') 
    version = models.CharField("Версия") 
    image = models.ImageField("Карточка", upload_to="image_version") 
    description = models.TextField("Описание") 
    file = models.FileField("Фаил обновления", upload_to="file_version") 

    def __str__(self): 
        return f"{self.application} {self.version}"


class DarkAccount(AbstractUser):
    class AccessChoices(models.TextChoices):
        ALL = 'all', 'Все'
        AUTHENTICATED = 'authenticated', 'Аутентифицированные'
        NOBODY = 'nobody', 'Никто'

    class LanguageChoices(models.TextChoices):
        RUS = "Russian", "Русский"
        ENG = "English", "English"

    avatar = models.ImageField(
        upload_to=avatar_path,
        default=random_default_avatar,
        verbose_name="Аватар"
    )

    avatar_access = models.CharField("Доступ к аватару", choices=AccessChoices.choices, default=AccessChoices.ALL)

    info = models.TextField(
        blank=True,
        null=True,
        verbose_name="Информация"
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True,
        verbose_name="Дата рождения"
    )

    language = models.CharField(
        max_length=20,
        choices=LanguageChoices.choices,
        default=LanguageChoices.RUS
    )

    is_online = models.BooleanField(default=False)

    last_online = models.DateTimeField(
        null=True,
        blank=True
    )

    email_confirmed = models.BooleanField(default=False)

    two_factor_enabled = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        Group,
        related_name="darkaccount_groups",
        blank=True
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="darkaccount_permissions",
        blank=True
    )

    def __str__(self):
        return self.username


class Device(models.Model):

    class DeviceType(models.TextChoices):
        DESKTOP = "desktop", "Компьютер"
        MOBILE = "mobile", "Телефон"
        TABLET = "tablet", "Планшет"
        BOT = "bot", "Бот"
        UNKNOWN = "unknown", "Неизвестно"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="devices"
    )

    app_version = models.ForeignKey(
        Version,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    device_id = models.CharField(
        max_length=255,
        db_index=True
    )

    fingerprint = models.CharField(
        max_length=255,
        blank=True
    )

    name = models.CharField(
        max_length=255
    )

    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.UNKNOWN
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True
    )

    system_version = models.CharField(
        max_length=100,
        blank=True
    )

    browser = models.CharField(
        max_length=100,
        blank=True
    )

    browser_version = models.CharField(
        max_length=50,
        blank=True
    )

    application = models.CharField(
        max_length=100,
        blank=True
    )

    application_version = models.CharField(
        max_length=50,
        blank=True
    )

    user_agent = models.TextField(
        blank=True
    )

    first_ip = models.GenericIPAddressField()

    last_ip = models.GenericIPAddressField()

    country = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    timezone = models.CharField(
        max_length=100,
        blank=True
    )

    trusted = models.BooleanField(default=False)

    blocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return self.name


class EmailConfirmation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="email_confirmations"
    )

    code = models.CharField(
        max_length=10
    )

    expires_at = models.DateTimeField()

    confirmed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username


class PasswordReset(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="password_resets"
    )

    code = models.CharField(
        max_length=10
    )

    expires_at = models.DateTimeField()

    used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    used_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username


class LoginHistory(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Успешно"
        FAILED = "failed", "Ошибка"
        BLOCKED = "blocked", "Заблокировано"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        DarkAccount,
        on_delete=models.CASCADE,
        related_name="login_history"
    )

    device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    ip = models.GenericIPAddressField()

    user_agent = models.TextField()

    country = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices
    )

    reason = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.status})"