import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.utils.crypto import constant_time_compare

from account.api.serializers import DarkAccountPublicSerializer
from account.models import Token
from .events import chat_group_name, chats_user_name
from .models import ChatParticipant, Message, MessageRead


def serialize_message(message):
    return {
        'id': message.id,
        'chat_id': message.chat_id,
        'sender': DarkAccountPublicSerializer(message.sender).data if message.sender else None,
        'reply_to': message.reply_to_id,
        'message_type': message.message_type,
        'text': '' if message.is_deleted else message.text,
        'attachment': message.attachment.url if message.attachment and not message.is_deleted else None,
        'attachment_name': message.attachment_name if not message.is_deleted else '',
        'attachment_size': message.attachment_size if not message.is_deleted else None,
        'metadata': message.metadata,
        'is_edited': message.is_edited,
        'is_deleted': message.is_deleted,
        'created_at': message.created_at.isoformat(),
        'updated_at': message.updated_at.isoformat(),
        'reactions': [
            {
                'id': reaction.id,
                'user_id': reaction.user_id,
                'emoji': reaction.emoji,
                'created_at': reaction.created_at.isoformat(),
            }
            for reaction in message.reactions.all()
        ],
        'read_by': [read.user_id for read in message.read_by.all()],
    }


class AuthenticatedChatConsumer(AsyncJsonWebsocketConsumer):
    async def encode_json(self, content):
        return json.dumps(content, cls=DjangoJSONEncoder)

    async def authenticate(self):
        token = self._get_authorization_token()
        if token:
            if not self._has_valid_app_secret():
                return False
            self.user_id = await self.get_user_id_for_token(token)
            return self.user_id is not None

        user = self.scope.get('user')
        if user and user.is_authenticated and user.is_active:
            self.user_id = user.pk
            return True
        return False

    def _header(self, name):
        name = name.lower().encode('ascii')
        return next((value.decode('utf-8') for key, value in self.scope.get('headers', []) if key.lower() == name), None)

    def _get_authorization_token(self):
        authorization = self._header('authorization')
        if not authorization:
            return None
        scheme, separator, token = authorization.partition(' ')
        if separator and scheme.lower() == 'token' and token.strip():
            return token.strip()
        return None

    def _has_valid_app_secret(self):
        supplied = self._header('dark-talk-secret-key')
        if not supplied:
            return False
        secret = supplied.split('--', 1)[0]
        return constant_time_compare(secret, settings.DARK_TALK_SECRET_KEY)

    @database_sync_to_async
    def get_user_id_for_token(self, token):
        return Token.objects.filter(
            key=token,
            device__blocked=False,
            device__user__is_active=True,
        ).values_list('device__user_id', flat=True).first()

    async def chat_message(self, event):
        await self.send_json(event['payload'])

    async def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)


class ChatsConsumer(AuthenticatedChatConsumer):
    async def connect(self):
        if not await self.authenticate():
            await self.close(code=4001)
            return
        self.group_name = chats_user_name(self.user_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection_ready', 'scope': 'chats'})


class ChatConsumer(AuthenticatedChatConsumer):
    async def connect(self):
        if not await self.authenticate():
            await self.close(code=4001)
            return
        self.chat_id = int(self.scope['url_route']['kwargs']['chat_id'])
        if not await self.is_member(self.chat_id, self.user_id):
            await self.close(code=4003)
            return
        self.group_name = chat_group_name(self.chat_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connection_ready', 'chat_id': self.chat_id})

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self.send_error('invalid_payload')
            return
        if not await self.is_member(self.chat_id, self.user_id):
            await self.close(code=4003)
            return

        event_type = content.get('type')
        handlers = {
            'send_message': self.send_message,
            'typing': self.send_typing,
            'read_message': self.mark_read,
            'edit_message': self.edit_message,
            'delete_message': self.delete_message,
        }
        handler = handlers.get(event_type)
        if handler is None:
            await self.send_error('unknown_event')
            return
        await handler(content)

    async def send_error(self, code, message=None):
        payload = {'type': 'error', 'code': code}
        if message:
            payload['message'] = message
        await self.send_json(payload)

    async def send_typing(self, content):
        is_typing = content.get('is_typing') is True
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat.message',
                'payload': {
                    'type': 'typing',
                    'chat_id': self.chat_id,
                    'user_id': self.user_id,
                    'is_typing': is_typing,
                },
            },
        )

    async def send_message(self, content):
        text = content.get('text')
        if not isinstance(text, str) or not text.strip():
            await self.send_error('empty_text')
            return
        if content.get('message_type', 'text') != Message.MessageType.TEXT:
            await self.send_error('unsupported_message_type', 'Вложения отправляйте через HTTP API.')
            return

        message_data = await self.create_message(text.strip(), content.get('reply_to'))
        if message_data is None:
            await self.send_error('invalid_reply')
            return
        payload = {
            'type': 'message_created',
            'chat_id': self.chat_id,
            'message': message_data,
            'client_message_id': content.get('client_message_id'),
        }
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat.message', 'payload': payload},
        )
        for user_id in await self.participant_ids():
            await self.channel_layer.group_send(
                chats_user_name(user_id),
                {'type': 'chat.message', 'payload': payload},
            )

    async def edit_message(self, content):
        message_data = await self.update_message(content.get('message_id'), content.get('text'))
        if message_data is None:
            await self.send_error('edit_forbidden')
            return
        payload = {'type': 'message_updated', 'chat_id': self.chat_id, 'message': message_data}
        await self.channel_layer.group_send(self.group_name, {'type': 'chat.message', 'payload': payload})
        for user_id in await self.participant_ids():
            await self.channel_layer.group_send(
                chats_user_name(user_id),
                {'type': 'chat.message', 'payload': payload},
            )

    async def delete_message(self, content):
        message_id = content.get('message_id')
        if not await self.remove_message(message_id):
            await self.send_error('delete_forbidden')
            return
        payload = {'type': 'message_deleted', 'chat_id': self.chat_id, 'message_id': message_id}
        await self.channel_layer.group_send(self.group_name, {'type': 'chat.message', 'payload': payload})
        for user_id in await self.participant_ids():
            await self.channel_layer.group_send(
                chats_user_name(user_id),
                {'type': 'chat.message', 'payload': payload},
            )

    async def mark_read(self, content):
        result = await self.set_read(content.get('message_id'))
        if result is None:
            await self.send_error('invalid_message')
            return
        payload = {
            'type': 'message_read',
            'chat_id': self.chat_id,
            'message_id': result['message_id'],
            'user_id': self.user_id,
            'read_at': result['read_at'],
        }
        await self.channel_layer.group_send(self.group_name, {'type': 'chat.message', 'payload': payload})
        for user_id in await self.participant_ids():
            await self.channel_layer.group_send(
                chats_user_name(user_id),
                {'type': 'chat.message', 'payload': payload},
            )

    @database_sync_to_async
    def is_member(self, chat_id, user_id):
        return ChatParticipant.objects.filter(
            chat_id=chat_id,
            user_id=user_id,
            left_at__isnull=True,
        ).exists()

    @database_sync_to_async
    def participant_ids(self):
        return list(
            ChatParticipant.objects.filter(
                chat_id=self.chat_id,
                left_at__isnull=True,
            ).values_list('user_id', flat=True)
        )

    @database_sync_to_async
    def create_message(self, text, reply_to_id=None):
        reply_to = None
        if reply_to_id is not None:
            try:
                reply_to_id = int(reply_to_id)
            except (TypeError, ValueError):
                return None
            reply_to = Message.objects.filter(id=reply_to_id, chat_id=self.chat_id).first()
            if reply_to is None:
                return None
        message = Message.objects.create(
            chat_id=self.chat_id,
            sender_id=self.user_id,
            reply_to=reply_to,
            message_type=Message.MessageType.TEXT,
            text=text,
        )
        message.chat.save(update_fields=['updated_at'])
        return serialize_message(message)

    @database_sync_to_async
    def update_message(self, message_id, text):
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return None
        if not isinstance(text, str) or not text.strip():
            return None
        message = Message.objects.filter(
            id=message_id,
            chat_id=self.chat_id,
            sender_id=self.user_id,
            is_deleted=False,
        ).first()
        if message is None:
            return None
        message.text = text.strip()
        message.is_edited = True
        message.save(update_fields=['text', 'is_edited', 'updated_at'])
        return serialize_message(message)

    @database_sync_to_async
    def remove_message(self, message_id):
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return False
        message = Message.objects.filter(
            id=message_id,
            chat_id=self.chat_id,
            sender_id=self.user_id,
            is_deleted=False,
        ).first()
        if message is None:
            return False
        message.is_deleted = True
        message.text = ''
        message.save(update_fields=['is_deleted', 'text', 'updated_at'])
        return True

    @database_sync_to_async
    def set_read(self, message_id):
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return None
        message = Message.objects.filter(id=message_id, chat_id=self.chat_id).first()
        if message is None:
            return None
        message_read, _ = MessageRead.objects.get_or_create(message=message, user_id=self.user_id)
        ChatParticipant.objects.filter(
            chat_id=self.chat_id,
            user_id=self.user_id,
            left_at__isnull=True,
        ).filter(
            Q(last_read_message__isnull=True) | Q(last_read_message_id__lt=message.id)
        ).update(last_read_message=message)
        return {'message_id': message.id, 'read_at': message_read.read_at.isoformat()}