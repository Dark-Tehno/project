import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder

from .models import ChatParticipant


logger = logging.getLogger(__name__)


def chat_group_name(chat_id):
    return f'chat.{chat_id}'


def chats_user_name(user_id):
    return f'chats.user.{user_id}'


def publish_chat_event(chat_id, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = json.loads(json.dumps(payload, cls=DjangoJSONEncoder))
    user_ids = list(
        ChatParticipant.objects.filter(
            chat_id=chat_id,
            left_at__isnull=True,
        ).values_list('user_id', flat=True)
    )

    async def publish():
        event = {'type': 'chat.message', 'payload': payload}
        await channel_layer.group_send(chat_group_name(chat_id), event)
        for user_id in user_ids:
            await channel_layer.group_send(chats_user_name(user_id), event)

    try:
        async_to_sync(publish)()
    except Exception:
        logger.exception('Failed to publish chat event for chat %s', chat_id)