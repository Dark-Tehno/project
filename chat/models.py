from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Chat(models.Model):
    class ChatType(models.TextChoices):
        DIRECT = 'direct', 'Личный чат'
        GROUP = 'group', 'Групповой чат'

    id = models.BigAutoField(primary_key=True)
    chat_type = models.CharField(
        max_length=10,
        choices=ChatType.choices,
        default=ChatType.DIRECT,
        db_index=True,
        verbose_name='Тип чата',
    )
    title = models.CharField(max_length=150, blank=True, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    avatar = models.ImageField(
        upload_to='chat_avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар чата',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_chats',
        verbose_name='Создатель',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        return self.title or f'Чат #{self.pk}'


class ChatParticipant(models.Model):
    class Role(models.TextChoices):
        MEMBER = 'member', 'Участник'
        ADMIN = 'admin', 'Администратор'
        OWNER = 'owner', 'Владелец'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_participations',
        verbose_name='Пользователь',
    )
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='participant', verbose_name='Чат')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER, verbose_name='Роль')
    is_muted = models.BooleanField(default=False, verbose_name='Без уведомлений')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата присоединения')
    left_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата выхода')
    last_read_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name='Последнее прочитанное сообщение',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('chat', 'user'), name='unique_chat_participant'),
        ]
        indexes = [models.Index(fields=('user', 'chat'))]
        verbose_name = 'Участник чата'
        verbose_name_plural = 'Участники чатов'

    def __str__(self):
        return f'{self.user} в {self.chat}'


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Текст'
        IMAGE = 'image', 'Изображение'
        FILE = 'file', 'Файл'
        SYSTEM = 'system', 'Системное'

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_messages',
        verbose_name='Отправитель',
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Ответ на сообщение',
    )
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT, verbose_name='Тип сообщения')
    text = models.TextField(blank=True, verbose_name='Текст')
    attachment = models.FileField(upload_to='chat_files/%Y/%m/', blank=True, null=True, verbose_name='Вложение')
    attachment_name = models.CharField(max_length=255, blank=True, verbose_name='Название вложения')
    attachment_size = models.PositiveBigIntegerField(null=True, blank=True, validators=[MinValueValidator(0)], verbose_name='Размер вложения')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Метаданные')
    is_edited = models.BooleanField(default=False, verbose_name='Отредактировано')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        ordering = ('created_at',)
        indexes = [
            models.Index(fields=('chat', '-created_at')),
            models.Index(fields=('sender', '-created_at')),
        ]
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return f'Сообщение #{self.pk} в {self.chat}'


class MessageRead(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_by', verbose_name='Сообщение')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='read_messages',
        verbose_name='Пользователь',
    )
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата прочтения')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('message', 'user'), name='unique_message_read'),
        ]
        indexes = [models.Index(fields=('user', '-read_at'))]
        verbose_name = 'Прочтение сообщения'
        verbose_name_plural = 'Прочтения сообщений'


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions', verbose_name='Сообщение')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_reactions',
        verbose_name='Пользователь',
    )
    emoji = models.CharField(max_length=32, verbose_name='Эмодзи')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('message', 'user', 'emoji'),
                name='unique_message_reaction',
            ),
        ]
        verbose_name = 'Реакция на сообщение'
        verbose_name_plural = 'Реакции на сообщения'


