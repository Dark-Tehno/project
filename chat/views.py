from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from account.utils import StandartAPIPermission
from account.models import DarkAccount
from account.serializers import DarkAccountSerializer
from .models import Chat, ChatParticipant, Message, MessageRead, MessageReaction
from django.shortcuts import get_object_or_404


# Create your views here.
class ChatView(APIView):
    permission_classes = [StandartAPIPermission]

    def post(self, request):
        chat_type = request.data.get('chat_type', 'direct')
        user = request.user

        if chat_type == 'direct':
            participant_name = request.data.get('participant_name', None)
            if participant_name is None:
                return Response({'status': 'error', 'message': 'PARTICIPANT_NAME_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

            participant = DarkAccount.objects.get(username=participant_name)
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
            'avatar': chat.avatar.url if chat.chat_type == "group" else None,
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
        participant_is_admin = True if participant.role is ['admin', 'owner'] else False
        if participant_is_admin:
            if new_participants is not None:
                participant_names = new_participants.split(',')
                for participant_name in participant_names:
                    participant_name = participant_name.strip()
                    if participant_name == request.user.username:
                        continue
                    try:
                        participant = DarkAccount.objects.get(username=participant_name)
                        ChatParticipant.objects.get_or_create(user=participant, chat=chat, role='member')
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
                        ChatParticipant.objects.delete(user=participant, chat=chat, role='member')
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
                if role is ['admin', 'member']:

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
