from datetime import date

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from account.models import DarkAccount
from .models import BlockedUser, Chat, ChatParticipant, Message, MessageRead, MessageReaction


class ChatApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.owner = DarkAccount.objects.create_user(username='owner', password='test-password')
		self.member = DarkAccount.objects.create_user(username='member', password='test-password')
		self.outsider = DarkAccount.objects.create_user(username='outsider', password='test-password')
		self.chat = Chat.objects.create(chat_type=Chat.ChatType.GROUP, title='Test chat', created_by=self.owner)
		ChatParticipant.objects.create(chat=self.chat, user=self.owner, role=ChatParticipant.Role.OWNER)
		ChatParticipant.objects.create(chat=self.chat, user=self.member)
		self.client.force_authenticate(self.member)
		self.client.defaults['HTTP_DARK_TALK_SECRET_KEY'] = f'{settings.DARK_TALK_SECRET_KEY}--test|1'

	def test_message_history_is_paginated_and_oldest_cursor_continues(self):
		messages = [
			Message.objects.create(chat=self.chat, sender=self.owner, text=f'message {index}')
			for index in range(3)
		]

		response = self.client.get(f'/chat/api/chats/{self.chat.id}/messages/?limit=2')

		self.assertEqual(response.status_code, 200)
		self.assertEqual([message['id'] for message in response.data['messages']], [messages[1].id, messages[2].id])
		self.assertTrue(response.data['has_more'])
		next_response = self.client.get(
			f"/chat/api/chats/{self.chat.id}/messages/?limit=2&before_id={response.data['next_before_id']}"
		)
		self.assertEqual([message['id'] for message in next_response.data['messages']], [messages[0].id])

	def test_chat_read_marks_incoming_messages_and_updates_cursor(self):
		message = Message.objects.create(chat=self.chat, sender=self.owner, text='hello')

		response = self.client.post(f'/chat/api/chats/{self.chat.id}/read/')

		self.assertEqual(response.status_code, 200)
		self.assertTrue(MessageRead.objects.filter(message=message, user=self.member).exists())
		self.assertEqual(
			ChatParticipant.objects.get(chat=self.chat, user=self.member).last_read_message_id,
			message.id,
		)

	def test_member_can_edit_own_message_but_not_another_users_message(self):
		own_message = Message.objects.create(chat=self.chat, sender=self.member, text='before')
		other_message = Message.objects.create(chat=self.chat, sender=self.owner, text='private')

		own_response = self.client.patch(
			f'/chat/api/messages/{own_message.id}/',
			{'text': 'after'},
			format='json',
		)
		other_response = self.client.patch(
			f'/chat/api/messages/{other_message.id}/',
			{'text': 'changed'},
			format='json',
		)

		self.assertEqual(own_response.status_code, 200)
		self.assertEqual(own_response.data['message']['text'], 'after')
		self.assertEqual(other_response.status_code, 403)

	def test_nonparticipant_cannot_read_chat_messages(self):
		self.client.force_authenticate(self.outsider)

		response = self.client.get(f'/chat/api/chats/{self.chat.id}/messages/')

		self.assertEqual(response.status_code, 404)

	def test_chat_list_includes_unread_count(self):
		Message.objects.create(chat=self.chat, sender=self.owner, text='incoming')
		Message.objects.create(chat=self.chat, sender=self.member, text='outgoing')

		response = self.client.get('/chat/api/chats/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['chats'][0]['unread_count'], 1)

	def test_chat_responses_only_include_public_account_fields(self):
		self.owner.email = 'private@example.com'
		self.owner.info = 'Private profile information'
		self.owner.date_of_birth = date(1990, 1, 1)
		self.owner.two_factor_enabled = True
		self.owner.avatar_access = DarkAccount.AccessChoices.NOBODY
		self.owner.save()

		list_response = self.client.get('/chat/api/chats/')
		detail_response = self.client.get(f'/chat/api/chats/{self.chat.id}/')
		message = Message.objects.create(chat=self.chat, sender=self.owner, text='hello')
		messages_response = self.client.get(f'/chat/api/chats/{self.chat.id}/messages/')

		self.assertEqual(list_response.status_code, 200)
		self.assertEqual(detail_response.status_code, 200)
		self.assertEqual(messages_response.status_code, 200)
		public_users = [
			participant['user']
			for participant in list_response.data['chats'][0]['participants']
		]
		public_users.extend(
			participant['user']
			for participant in detail_response.data['participants']
		)
		public_users.extend([
			detail_response.data['created_by']['user'],
			messages_response.data['messages'][0]['sender'],
		])
		for public_user in public_users:
			self.assertEqual(set(public_user), {'id', 'username', 'avatar', 'is_online'})
			self.assertNotIn('private@example.com', str(public_user))
		self.assertIsNone(next(user for user in public_users if user['id'] == self.owner.id)['avatar'])
		self.assertEqual(messages_response.data['messages'][0]['id'], message.id)

	def test_user_can_remove_own_reaction(self):
		message = Message.objects.create(chat=self.chat, sender=self.owner, text='hello')
		reaction = MessageReaction.objects.create(message=message, user=self.member, emoji='❤️')

		response = self.client.delete(
			f'/chat/api/messages/reaction/{message.id}/',
			{'emoji': reaction.emoji},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(MessageReaction.objects.filter(id=reaction.id).exists())

	def test_owner_can_change_member_role_and_mute_state(self):
		self.client.force_authenticate(self.owner)

		response = self.client.patch(
			f'/chat/api/chats/{self.chat.id}/participants/{self.member.id}/',
			{'role': ChatParticipant.Role.ADMIN, 'is_muted': True},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['role'], ChatParticipant.Role.ADMIN)
		self.assertTrue(response.data['is_muted'])

	def test_user_can_block_and_unblock_another_user(self):
		block_url = '/chat/api/chats/blocked/outsider/'
		unblock_url = '/chat/api/chats/unblocked/outsider/'

		block_response = self.client.post(block_url)
		repeated_block_response = self.client.post(block_url)

		self.assertEqual(block_response.status_code, 200)
		self.assertEqual(repeated_block_response.status_code, 200)
		self.assertTrue(
			BlockedUser.objects.filter(user=self.member, blocked_user=self.outsider).exists()
		)
		self.assertEqual(
			BlockedUser.objects.filter(user=self.member, blocked_user=self.outsider).count(),
			1,
		)

		unblock_response = self.client.post(unblock_url)

		self.assertEqual(unblock_response.status_code, 200)
		self.assertFalse(
			BlockedUser.objects.filter(user=self.member, blocked_user=self.outsider).exists()
		)

	def test_user_cannot_block_themselves(self):
		response = self.client.post('/chat/api/chats/blocked/member/')

		self.assertEqual(response.status_code, 400)
		self.assertFalse(BlockedUser.objects.filter(user=self.member).exists())
