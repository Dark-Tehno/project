from asgiref.sync import async_to_sync, sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from account.models import DarkAccount, Device, Token
from .consumers import serialize_message
from .models import Chat, ChatParticipant, Message, MessageRead
from .routing import websocket_urlpatterns


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = DarkAccount.objects.create_user(username='socket-user', password='test-password')
        self.other_user = DarkAccount.objects.create_user(username='socket-peer', password='test-password')
        self.device = Device.objects.create(
            user=self.user,
            device_id='socket-test-device',
            name='Socket test device',
            first_ip='127.0.0.1',
            last_ip='127.0.0.1',
        )
        self.token = Token.objects.create(key='socket-test-token', device=self.device)
        self.other_device = Device.objects.create(
            user=self.other_user,
            device_id='socket-peer-device',
            name='Socket peer device',
            first_ip='127.0.0.1',
            last_ip='127.0.0.1',
        )
        self.other_token = Token.objects.create(key='socket-peer-token', device=self.other_device)
        self.chat = Chat.objects.create(chat_type=Chat.ChatType.DIRECT, created_by=self.user)
        ChatParticipant.objects.create(chat=self.chat, user=self.user, role=ChatParticipant.Role.OWNER)
        ChatParticipant.objects.create(chat=self.chat, user=self.other_user)
        self.headers = [
            (b'authorization', f'Token {self.token.key}'.encode()),
            (
                b'dark-talk-secret-key',
                f'{settings.DARK_TALK_SECRET_KEY}--test|1'.encode(),
            ),
        ]
        self.other_headers = [
            (b'authorization', f'Token {self.other_token.key}'.encode()),
            (
                b'dark-talk-secret-key',
                f'{settings.DARK_TALK_SECRET_KEY}--test|1'.encode(),
            ),
        ]
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)
        self.api_client.defaults['HTTP_DARK_TALK_SECRET_KEY'] = f'{settings.DARK_TALK_SECRET_KEY}--test|1'

    def test_member_authenticates_and_sends_message_to_chat(self):
        chats_communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            '/ws/chats/',
            headers=self.headers,
        )
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.chat.id}/',
            headers=self.headers,
        )

        async def exchange_message():
            chats_connected, _ = await chats_communicator.connect()
            if not chats_connected:
                return False, None, None
            chats_ready = await chats_communicator.receive_json_from()
            connected, _ = await communicator.connect()
            if not connected:
                return False, None, None
            ready_event = await communicator.receive_json_from()
            await communicator.send_json_to({'type': 'send_message', 'text': 'hello'})
            message_event = await communicator.receive_json_from()
            chats_event = await chats_communicator.receive_json_from()
            await communicator.disconnect()
            await chats_communicator.disconnect()
            return chats_ready, ready_event, message_event, chats_event

        chats_ready, ready, event, chats_event = async_to_sync(exchange_message)()
        self.assertEqual(chats_ready, {'type': 'connection_ready', 'scope': 'chats'})
        self.assertEqual(ready, {'type': 'connection_ready', 'chat_id': self.chat.id})
        self.assertEqual(event['type'], 'message_created')
        self.assertEqual(event['message']['text'], 'hello')
        self.assertEqual(event['message']['sender']['username'], self.user.username)
        self.assertEqual(chats_event['type'], 'message_created')
        self.assertEqual(chats_event['chat_id'], self.chat.id)
        self.assertEqual(Message.objects.filter(chat=self.chat, text='hello').count(), 1)

    def test_message_serializer_returns_json_safe_timestamps(self):
        message = Message.objects.create(chat=self.chat, sender=self.user, text='timestamp check')

        serialized = serialize_message(message)

        self.assertIsInstance(serialized['created_at'], str)
        self.assertIsInstance(serialized['updated_at'], str)
        self.assertEqual(
            set(serialized['sender']),
            {'id', 'username', 'avatar', 'is_online'},
        )

    def test_non_member_is_rejected(self):
        outsider = DarkAccount.objects.create_user(username='socket-outsider', password='test-password')
        device = Device.objects.create(
            user=outsider,
            device_id='socket-outsider-device',
            name='Socket outsider device',
            first_ip='127.0.0.1',
            last_ip='127.0.0.1',
        )
        token = Token.objects.create(key='socket-outsider-token', device=device)
        headers = [
            (b'authorization', f'Token {token.key}'.encode()),
            (
                b'dark-talk-secret-key',
                f'{settings.DARK_TALK_SECRET_KEY}--test|1'.encode(),
            ),
        ]
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.chat.id}/',
            headers=headers,
        )

        connected, close_code = async_to_sync(communicator.connect)()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4003)

    def test_invalid_app_secret_is_rejected(self):
        headers = [
            (b'authorization', f'Token {self.token.key}'.encode()),
            (b'dark-talk-secret-key', b'invalid-secret--test|1'),
        ]
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            '/ws/chats/',
            headers=headers,
        )

        connected, close_code = async_to_sync(communicator.connect)()

        self.assertFalse(connected)
        self.assertEqual(close_code, 4001)

    def test_read_message_event_persists_receipt_and_cursor(self):
        message = Message.objects.create(chat=self.chat, sender=self.other_user, text='incoming')
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.chat.id}/',
            headers=self.headers,
        )

        async def mark_message_read():
            connected, _ = await communicator.connect()
            if not connected:
                return None
            await communicator.receive_json_from()
            await communicator.send_json_to({'type': 'read_message', 'message_id': message.id})
            event = await communicator.receive_json_from()
            await communicator.disconnect()
            return event

        event = async_to_sync(mark_message_read)()

        self.assertEqual(event['type'], 'message_read')
        self.assertEqual(event['message_id'], message.id)
        self.assertTrue(MessageRead.objects.filter(message=message, user=self.user).exists())
        participant = ChatParticipant.objects.get(chat=self.chat, user=self.user)
        self.assertEqual(participant.last_read_message_id, message.id)

    def test_http_message_is_delivered_to_connected_chat_consumer(self):
        communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            f'/ws/chat/{self.chat.id}/',
            headers=self.other_headers,
        )

        async def send_http_message():
            connected, _ = await communicator.connect()
            if not connected:
                return None, None
            await communicator.receive_json_from()
            response = await sync_to_async(self.api_client.post, thread_sensitive=True)(
                '/chat/api/messages/create/',
                {
                    'chat_id': self.chat.id,
                    'text': 'sent through HTTP',
                    'client_message_id': 'http-client-1',
                },
                format='json',
            )
            event = await communicator.receive_json_from()
            await communicator.disconnect()
            return response, event

        response, event = async_to_sync(send_http_message)()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(event['type'], 'message_created')
        self.assertEqual(event['message']['text'], 'sent through HTTP')
        self.assertEqual(event['client_message_id'], 'http-client-1')

    def test_http_chat_creation_is_delivered_to_participant_chat_streams(self):
        owner_communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            '/ws/chats/',
            headers=self.headers,
        )
        member_communicator = WebsocketCommunicator(
            URLRouter(websocket_urlpatterns),
            '/ws/chats/',
            headers=self.other_headers,
        )

        async def create_chat():
            owner_connected, _ = await owner_communicator.connect()
            member_connected, _ = await member_communicator.connect()
            if not owner_connected or not member_connected:
                return None, None, None
            await owner_communicator.receive_json_from()
            await member_communicator.receive_json_from()
            response = await sync_to_async(self.api_client.post, thread_sensitive=True)(
                '/chat/api/chats/create/',
                {
                    'chat_type': 'group',
                    'participant_names': self.other_user.username,
                    'title': 'WebSocket test chat',
                },
                format='json',
            )
            owner_event = await owner_communicator.receive_json_from()
            member_event = await member_communicator.receive_json_from()
            await owner_communicator.disconnect()
            await member_communicator.disconnect()
            return response, owner_event, member_event

        response, owner_event, member_event = async_to_sync(create_chat)()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(owner_event['type'], 'chat_created')
        self.assertEqual(owner_event['chat_id'], response.data['chat_id'])
        self.assertEqual(owner_event['chat']['chat_type'], Chat.ChatType.GROUP)
        self.assertEqual(owner_event['chat']['title'], 'WebSocket test chat')
        self.assertEqual(
            {participant['user']['id'] for participant in owner_event['chat']['participants']},
            {self.user.id, self.other_user.id},
        )
        self.assertEqual(member_event, owner_event)