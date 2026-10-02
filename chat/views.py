from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, F, Q, Value
from django.db.models.functions import Coalesce
from django.db import transaction

from account.utils import DeviceTokenAuthentication, StandartAPIPermission
from account.models import DarkAccount
from account.api.serializers import DarkAccountPublicSerializer, DarkAccountSerializer
from .models import Chat, ChatParticipant, Message, MessageRead, MessageReaction
from .events import publish_chat_event
from django.shortcuts import get_object_or_404


def serialize_message(message):
    return {
        'id': message.id,
        'chat_id': message.chat_id,
        'sender': DarkAccountSerializer(message.sender).data if message.sender else None,
        'reply_to': message.reply_to_id,
        'message_type': message.message_type,
        'text': '' if message.is_deleted else message.text,
        'attachment': message.attachment.url if message.attachment and not message.is_deleted else None,
        'attachment_name': message.attachment_name if not message.is_deleted else '',
        'attachment_size': message.attachment_size if not message.is_deleted else None,
        'metadata': message.metadata,
        'is_edited': message.is_edited,
        'is_deleted': message.is_deleted,
        'created_at': message.created_at,
        'updated_at': message.updated_at,
        'reactions': [
            {
                'id': reaction.id,
                'user_id': reaction.user_id,
                'emoji': reaction.emoji,
                'created_at': reaction.created_at,
            }
            for reaction in message.reactions.all()
        ],
        'read_by': [read.user_id for read in message.read_by.all()],
    }


# Create your views here.
class ChatView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request):
        chat_type = request.data.get('chat_type', 'direct')
        user = request.user

        if chat_type == 'direct':
            participant_name = request.data.get('participant_name', None)
            if participant_name is None:
                return Response({'status': 'error', 'message': 'PARTICIPANT_NAME_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

            participant = get_object_or_404(DarkAccount, username=participant_name)
            if participant == user:
                return Response({'status': 'error', 'message': 'CANNOT_CREATE_CHAT_WITH_SELF'}, status=status.HTTP_400_BAD_REQUEST)
            existing_chat = Chat.objects.filter(
                chat_type=Chat.ChatType.DIRECT,
                participant__user=user,
            ).filter(participant__user=participant).first()
            if existing_chat:
                return Response({'status': 'success', 'chat_id': existing_chat.id}, status=status.HTTP_200_OK)
            chat = Chat.objects.create(chat_type=chat_type, created_by=user)
            ChatParticipant.objects.create(user=user, chat=chat, role='owner')
            ChatParticipant.objects.create(user=participant, chat=chat, role='member')
            return Response({'status': 'success', 'chat_id': chat.id}, status=status.HTTP_201_CREATED)
        elif chat_type == 'group':
            participant_names = request.data.get('participant_names', None)
            title = request.data.get('title', None)
            description = request.data.get('description', '')
            avatar = request.data.get('avatar', None)

            if participant_names is None:
                return Response({'status': 'error', 'message': 'PARTICIPANT_NAMES_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

            if title is None or title.strip() == '':
                title = f'Chat by {user.username}'

            chat = Chat.objects.create(chat_type=chat_type, title=title, description=description, avatar=avatar, created_by=user)
            ChatParticipant.objects.create(user=user, chat=chat, role='owner')
            participant_names = participant_names.split(',')
            for participant_name in participant_names:
                participant_name = participant_name.strip()
                if participant_name == user.username:
                    continue
                try:
                    participant = DarkAccount.objects.get(username=participant_name)
                    ChatParticipant.objects.create(user=participant, chat=chat, role='member')
                except DarkAccount.DoesNotExist:
                    continue
            return Response({'status': 'success', 'chat_id': chat.id}, status=status.HTTP_201_CREATED)
        return Response({'status': 'error', 'message': 'INVALID_CHAT_TYPE'}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, id):
        chat = get_object_or_404(
            Chat,
            id=id,
            participant__user=request.user
        )
        return Response({
            'status': 'success',
            'id': chat.id,
            'chat_type': chat.chat_type,
            'title': chat.title if chat.chat_type == "group" else None,
            'description': chat.description if chat.chat_type == "group" else None,
            'avatar': chat.avatar.url if chat.chat_type == "group" and chat.avatar else None,
            'created_by': {
                'user': DarkAccountSerializer(chat.created_by).data
            } if chat.chat_type == "group" else None,
            'created_at': chat.created_at,
            'updated_at': chat.updated_at,
            'participants': [
                {
                    'user': DarkAccountSerializer(participant.user).data,
                    'role': participant.role,
                    'joined_at': participant.joined_at,
                    'is_muted': participant.is_muted,
                }
                for participant in chat.participant.all()
            ]
        }, status=status.HTTP_200_OK)

    def patch(self, request, id):
        new_participants = request.data.get('new_participants', None)
        new_title = request.data.get('new_title', None)
        new_description = request.data.get('new_description', None)
        new_avatar = request.data.get('new_avatar', None)
        new_role = request.data.get('new_role', None)
        del_participants = request.data.get('del_participants', None)
        
        chat = get_object_or_404(
            Chat,
            id=id,
            participant__user=request.user
        )
        participant = get_object_or_404(
            ChatParticipant,
            user = request.user,
            chat = chat
        )
        participant_is_admin = True if participant.role == 'admin' or participant.role == 'owner' else False
        if participant_is_admin:
            if new_participants is not None:
                participant_names = new_participants.split(',')
                for participant_name in participant_names:
                    participant_name = participant_name.strip()
                    if participant_name == request.user.username:
                        continue
                    try:
                        participant = DarkAccount.objects.get(username=participant_name)
                        ChatParticipant.objects.get_or_create(
                            user=participant,
                            chat=chat,
                            defaults={'role': ChatParticipant.Role.MEMBER},
                        )
                    except DarkAccount.DoesNotExist:
                        continue

            if del_participants is not None:
                participant_names = del_participants.split(',')
                for participant_name in participant_names:
                    participant_name = participant_name.strip()
                    if participant_name == request.user.username:
                        continue
                    try:
                        participant = DarkAccount.objects.get(username=participant_name)
                        ChatParticipant.objects.filter(
                            user=participant,
                            chat=chat,
                            role=ChatParticipant.Role.MEMBER,
                        ).delete()
                    except DarkAccount.DoesNotExist:
                        continue

            if new_title is not None:
                chat.title = new_title
                chat.save()
            if new_description is not None:
                chat.description = new_description
                chat.save()
            if new_avatar is not None:
                chat.avatar = new_avatar
                chat.save()

            if new_role is not None:
                participant_username, role = new_role.split(':')
                if role == 'admin' or role == 'member':

                    participant_user_account = DarkAccount.objects.get(username=participant_username)
                    participant_user = ChatParticipant.objects.get(
                        chat = chat,
                        user = participant_user_account
                    )
                    participant_user.role = role
                    participant_user.save()
            return Response({'status': 'success', 'chat_id': chat.id}, status=status.HTTP_200_OK)
        else:
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)

    def delete(self, request, id):
        chat = get_object_or_404(
            Chat,
            id=id,
            participant__user=request.user
        )
        participant = get_object_or_404(
            ChatParticipant,
            user = request.user,
            chat = chat
        )
        participant_is_admin = True if participant.role == 'admin' or participant.role == 'owner' else False

        if participant_is_admin:
            chat.delete()
            return Response({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)
        return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)


class ChatsView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request):
        chats = Chat.objects.filter(participant__user=request.user).select_related('created_by').prefetch_related(
            'participant__user',
        ).annotate(
            unread_count=Count(
                'messages',
                filter=(
                    Q(messages__id__gt=Coalesce(F('participant__last_read_message_id'), Value(0)))
                    & ~Q(messages__sender=request.user)
                ),
                distinct=True,
            ),
        ).distinct()
        return Response({
            'chats': [
                {
                    "id": chat.id,
                    "chat_type": chat.chat_type,
                    "title": chat.title if chat.chat_type == Chat.ChatType.GROUP else next(
                        (participant.user.username for participant in chat.participant.all() if participant.user_id != request.user.id),
                        '',
                    ),
                    "description": chat.description,
                    "avatar": chat.avatar.url if chat.avatar else None,
                    "created_by": DarkAccountPublicSerializer(chat.created_by).data if chat.created_by else None,
                    "created_at": chat.created_at,
                    "updated_at": chat.updated_at,
                    "unread_count": chat.unread_count,
                    "participants": [
                        {
                            'user': DarkAccountPublicSerializer(participant.user).data,
                            'role': participant.role,
                            'is_muted': participant.is_muted,
                        }
                        for participant in chat.participant.all()
                    ],
                }
                for chat in chats
            ]
            }, status=status.HTTP_200_OK)


class MessagesCreateView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request):
        chat_id = request.data.get('chat_id')
        if chat_id is None:
            return Response(
                {'status': 'error', 'message': 'CHAT_ID_NOT_PROVIDED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reply_to = request.data.get('reply_to', None)
        message_type = request.data.get('message_type', 'text')
        if message_type not in Message.MessageType.values:
            return Response(
                {'status': 'error', 'message': 'INVALID_MESSAGE_TYPE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        text = request.data.get('text', '')
        attachment = request.data.get('attachment', None)
        attachment_name = ''
        attachment_size = None
        metadata = request.data.get('metadata', {})

        if attachment is not None:
            attachment_name = attachment.name
            attachment_size = attachment.size

        chat = get_object_or_404(
            Chat,
            id=chat_id,
            participant__user=request.user,
        )
        reply_message = None
        if reply_to is not None:
            reply_message = get_object_or_404(Message, id=reply_to, chat=chat)

        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            reply_to=reply_message,
            message_type=message_type,
            text=text or '',
            attachment=attachment,
            attachment_name=attachment_name or '',
            attachment_size=attachment_size,
            metadata=metadata,
        )
        chat.save(update_fields=['updated_at'])
        event_payload = {
            'type': 'message_created',
            'chat_id': chat.id,
            'message': serialize_message(message),
            'client_message_id': request.data.get('client_message_id'),
        }
        transaction.on_commit(lambda: publish_chat_event(chat.id, event_payload))
        return Response(
            {'status': 'success', 'chat_id': chat.id, 'message_id': message.id},
            status=status.HTTP_201_CREATED,
        )


class MessagesReadView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request, id):
        message = get_object_or_404(
            Message,
            id=id,
            chat__participant__user=request.user,
        )
        message_read, _ = MessageRead.objects.get_or_create(
            message=message,
            user=request.user,
        )
        participant = get_object_or_404(ChatParticipant, chat=message.chat, user=request.user)
        if participant.last_read_message_id is None or participant.last_read_message_id < message.id:
            participant.last_read_message = message
            participant.save(update_fields=['last_read_message'])

        return Response(
            {
                'status': 'success',
                'message_id': message.id,
                'read_at': message_read.read_at,
            },
            status=status.HTTP_200_OK,
        )

class MessagesReactionView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request, id):
        emoji = request.data.get('emoji', '🔥')
        if not isinstance(emoji, str) or not emoji.strip() or len(emoji) > 32:
            return Response({'status': 'error', 'message': 'INVALID_EMOJI'}, status=status.HTTP_400_BAD_REQUEST)
        message = get_object_or_404(
            Message,
            id=id,
            chat__participant__user=request.user,
        )
        message_reaction, _ = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji
        )

        return Response(
            {
                'status': 'success',
                'message_id': message.id,
                'message_reaction': {
                    'id': message_reaction.id,
                    'user_id': message_reaction.user_id,
                    'emoji': message_reaction.emoji,
                    'created_at': message_reaction.created_at,
                },
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, id):
        emoji = request.data.get('emoji') or request.query_params.get('emoji')
        if not emoji:
            return Response({'status': 'error', 'message': 'EMOJI_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)
        message = get_object_or_404(
            Message,
            id=id,
            chat__participant__user=request.user,
        )
        deleted, _ = MessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji,
        ).delete()
        if not deleted:
            return Response({'status': 'error', 'message': 'REACTION_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'success'}, status=status.HTTP_200_OK)


class ChatMessagesView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request, id):
        chat = get_object_or_404(Chat, id=id, participant__user=request.user)
        try:
            limit = min(max(int(request.query_params.get('limit', 50)), 1), 100)
            before_id = request.query_params.get('before_id')
            before_id = int(before_id) if before_id is not None else None
            if before_id is not None and before_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'status': 'error', 'message': 'INVALID_PAGINATION'}, status=status.HTTP_400_BAD_REQUEST)

        messages = Message.objects.filter(chat=chat).select_related('sender', 'reply_to').prefetch_related(
            'reactions', 'read_by',
        ).order_by('-id')
        if before_id is not None:
            messages = messages.filter(id__lt=before_id)
        page = list(messages[:limit + 1])
        has_more = len(page) > limit
        page = list(reversed(page[:limit]))
        return Response({
            'status': 'success',
            'chat_id': chat.id,
            'messages': [serialize_message(message) for message in page],
            'has_more': has_more,
            'next_before_id': page[0].id if has_more and page else None,
        }, status=status.HTTP_200_OK)


class MessageView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def patch(self, request, id):
        message = get_object_or_404(Message, id=id, chat__participant__user=request.user)
        if message.sender_id != request.user.id:
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)
        if message.is_deleted:
            return Response({'status': 'error', 'message': 'MESSAGE_DELETED'}, status=status.HTTP_400_BAD_REQUEST)
        if 'text' not in request.data or not isinstance(request.data['text'], str):
            return Response({'status': 'error', 'message': 'TEXT_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)
        message.text = request.data['text']
        message.is_edited = True
        message.save(update_fields=['text', 'is_edited', 'updated_at'])
        return Response({'status': 'success', 'message': serialize_message(message)}, status=status.HTTP_200_OK)

    def delete(self, request, id):
        message = get_object_or_404(Message, id=id, chat__participant__user=request.user)
        participant = get_object_or_404(ChatParticipant, chat=message.chat, user=request.user)
        if message.sender_id != request.user.id and participant.role not in (ChatParticipant.Role.ADMIN, ChatParticipant.Role.OWNER):
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)
        if not message.is_deleted:
            message.is_deleted = True
            message.text = ''
            message.save(update_fields=['is_deleted', 'text', 'updated_at'])
        return Response({'status': 'success', 'message_id': message.id}, status=status.HTTP_200_OK)


class ChatReadView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request, id):
        chat = get_object_or_404(Chat, id=id, participant__user=request.user)
        participant = get_object_or_404(ChatParticipant, chat=chat, user=request.user)
        last_message_id = request.data.get('last_message_id')
        messages = Message.objects.filter(chat=chat).exclude(sender=request.user)
        if last_message_id is not None:
            try:
                last_message_id = int(last_message_id)
            except (TypeError, ValueError):
                return Response({'status': 'error', 'message': 'INVALID_LAST_MESSAGE_ID'}, status=status.HTTP_400_BAD_REQUEST)
            last_message = get_object_or_404(Message, id=last_message_id, chat=chat)
            messages = messages.filter(id__lte=last_message.id)
        else:
            last_message = Message.objects.filter(chat=chat).order_by('-id').first()

        unread_ids = messages.exclude(read_by__user=request.user).values_list('id', flat=True)
        MessageRead.objects.bulk_create(
            [MessageRead(message_id=message_id, user=request.user) for message_id in unread_ids],
            ignore_conflicts=True,
        )
        if last_message and (
            participant.last_read_message_id is None
            or participant.last_read_message_id < last_message.id
        ):
            participant.last_read_message = last_message
            participant.save(update_fields=['last_read_message'])
        return Response({
            'status': 'success',
            'chat_id': chat.id,
            'last_read_message_id': participant.last_read_message_id,
        }, status=status.HTTP_200_OK)


class ChatParticipantsView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request, id):
        chat = get_object_or_404(Chat, id=id, participant__user=request.user)
        requester = get_object_or_404(ChatParticipant, chat=chat, user=request.user)
        if requester.role not in (ChatParticipant.Role.ADMIN, ChatParticipant.Role.OWNER):
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)
        usernames = request.data.get('usernames', request.data.get('username'))
        if isinstance(usernames, str):
            usernames = [name.strip() for name in usernames.split(',') if name.strip()]
        if not isinstance(usernames, list) or not usernames:
            return Response({'status': 'error', 'message': 'USERNAMES_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)
        added = []
        for username in usernames:
            if not isinstance(username, str):
                continue
            user = DarkAccount.objects.filter(username=username.strip()).first()
            if user and user.id != request.user.id:
                participant, created = ChatParticipant.objects.get_or_create(
                    chat=chat,
                    user=user,
                    defaults={'role': ChatParticipant.Role.MEMBER},
                )
                if created:
                    added.append(user.username)
        return Response({'status': 'success', 'added': added}, status=status.HTTP_200_OK)

    def delete(self, request, id, user_id):
        chat = get_object_or_404(Chat, id=id, participant__user=request.user)
        requester = get_object_or_404(ChatParticipant, chat=chat, user=request.user)
        target = get_object_or_404(ChatParticipant, chat=chat, user_id=user_id)
        if target.user_id == request.user.id:
            if target.role == ChatParticipant.Role.OWNER:
                return Response({'status': 'error', 'message': 'OWNER_CANNOT_LEAVE'}, status=status.HTTP_400_BAD_REQUEST)
        elif requester.role not in (ChatParticipant.Role.ADMIN, ChatParticipant.Role.OWNER):
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)
        elif target.role == ChatParticipant.Role.OWNER:
            return Response({'status': 'error', 'message': 'CANNOT_REMOVE_OWNER'}, status=status.HTTP_400_BAD_REQUEST)
        target.delete()
        return Response({'status': 'success'}, status=status.HTTP_200_OK)

    def patch(self, request, id, user_id):
        chat = get_object_or_404(Chat, id=id, participant__user=request.user)
        requester = get_object_or_404(ChatParticipant, chat=chat, user=request.user)
        target = get_object_or_404(ChatParticipant, chat=chat, user_id=user_id)
        if requester.role not in (ChatParticipant.Role.ADMIN, ChatParticipant.Role.OWNER):
            return Response({'status': 'error', 'message': 'INSUFFICIENT_ACCOUNT_PERMISSIONS'}, status=status.HTTP_403_FORBIDDEN)

        role = request.data.get('role')
        is_muted = request.data.get('is_muted')
        if role is None and is_muted is None:
            return Response({'status': 'error', 'message': 'NO_PARTICIPANT_FIELDS_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)
        if role is not None:
            if requester.role != ChatParticipant.Role.OWNER:
                return Response({'status': 'error', 'message': 'ONLY_OWNER_CAN_CHANGE_ROLES'}, status=status.HTTP_403_FORBIDDEN)
            if target.role == ChatParticipant.Role.OWNER or role not in (ChatParticipant.Role.ADMIN, ChatParticipant.Role.MEMBER):
                return Response({'status': 'error', 'message': 'INVALID_PARTICIPANT_ROLE'}, status=status.HTTP_400_BAD_REQUEST)
            target.role = role
        if is_muted is not None:
            if not isinstance(is_muted, bool):
                return Response({'status': 'error', 'message': 'INVALID_MUTED_VALUE'}, status=status.HTTP_400_BAD_REQUEST)
            target.is_muted = is_muted
        target.save(update_fields=['role', 'is_muted'])
        return Response({
            'status': 'success',
            'user_id': target.user_id,
            'role': target.role,
            'is_muted': target.is_muted,
        }, status=status.HTTP_200_OK)