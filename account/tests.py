from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import DarkAccount, Device, LoginHistory, Token, TwoFactorCode


class AccountTwoFactorApiTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.client.defaults['HTTP_DARK_TALK_SECRET_KEY'] = (
			f'{settings.DARK_TALK_SECRET_KEY}--test|1'
		)
		self.user = DarkAccount.objects.create_user(
			username='two-factor-user',
			email='two-factor@example.com',
			password='test-password',
			two_factor_enabled=True,
		)

	@patch('account.two_factor.send_code_email')
	def test_login_with_two_factor_returns_challenge_without_token(self, send_code_email):
		response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)

		challenge = TwoFactorCode.objects.get(user=self.user)
		self.assertEqual(response.status_code, 202)
		self.assertEqual(response.data['status'], 'two_factor_required')
		self.assertEqual(response.data['challenge_id'], str(challenge.id))
		self.assertNotIn('token', response.data)
		self.assertFalse(Token.objects.filter(device__user=self.user).exists())
		send_code_email.assert_called_once()

	@patch('account.two_factor.send_code_email')
	def test_login_without_two_factor_still_returns_token(self, send_code_email):
		self.user.two_factor_enabled = False
		self.user.save(update_fields=['two_factor_enabled'])

		response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'success')
		self.assertTrue(response.data['token'])
		send_code_email.assert_not_called()

	def test_authenticated_user_can_enable_and_disable_two_factor(self):
		device = Device.objects.create(
			user=self.user,
			device_id='settings-device',
			name='Settings device',
			first_ip='127.0.0.1',
			last_ip='127.0.0.1',
		)
		token = Token.objects.create(key='settings-device-token', device=device)
		self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

		initial = self.client.get('/account/api/2fa/')
		enabled = self.client.patch(
			'/account/api/2fa/',
			{'enabled': False},
			format='json',
		)
		invalid = self.client.patch(
			'/account/api/2fa/',
			{'enabled': 'true'},
			format='json',
		)

		self.assertEqual(initial.status_code, 200)
		self.assertTrue(initial.data['two_factor_enabled'])
		self.assertEqual(enabled.status_code, 200)
		self.assertFalse(enabled.data['two_factor_enabled'])
		self.assertEqual(invalid.status_code, 400)

	@patch('account.two_factor.send_code_email')
	def test_disabling_two_factor_revokes_pending_challenge(self, send_code_email):
		login_response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)
		challenge = TwoFactorCode.objects.get(user=self.user)
		device = Device.objects.create(
			user=self.user,
			device_id='disable-device',
			name='Disable device',
			first_ip='127.0.0.1',
			last_ip='127.0.0.1',
		)
		token = Token.objects.create(key='disable-device-token', device=device)
		self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
		self.client.patch('/account/api/2fa/', {'enabled': False}, format='json')
		self.client.credentials(HTTP_AUTHORIZATION='')

		response = self.client.post(
			'/account/api/auth/2fa/verify/',
			{'challenge_id': login_response.data['challenge_id'], 'code': challenge.code},
			format='json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertTrue(TwoFactorCode.objects.get(pk=challenge.pk).used)
		self.assertFalse(Token.objects.filter(device__user=self.user).exclude(pk=token.pk).exists())
		send_code_email.assert_called_once()

	@patch('account.two_factor.send_code_email')
	def test_valid_code_issues_one_time_token(self, send_code_email):
		login_response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)
		challenge = TwoFactorCode.objects.get(user=self.user)

		response = self.client.post(
			'/account/api/auth/2fa/verify/',
			{'challenge_id': login_response.data['challenge_id'], 'code': challenge.code},
			format='json',
		)
		replay_response = self.client.post(
			'/account/api/auth/2fa/verify/',
			{'challenge_id': login_response.data['challenge_id'], 'code': challenge.code},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data['token'])
		self.assertEqual(response.data['user']['id'], self.user.id)
		self.assertTrue(challenge.__class__.objects.get(pk=challenge.pk).used)
		self.assertEqual(replay_response.status_code, 400)
		self.assertEqual(
			LoginHistory.objects.filter(user=self.user, status=LoginHistory.Status.SUCCESS).count(),
			1,
		)
		send_code_email.assert_called_once()

	@patch('account.two_factor.send_code_email')
	def test_invalid_code_does_not_issue_token(self, send_code_email):
		login_response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)

		response = self.client.post(
			'/account/api/auth/2fa/verify/',
			{'challenge_id': login_response.data['challenge_id'], 'code': '000000'},
			format='json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['message'], 'INVALID_OR_EXPIRED_TWO_FACTOR_CODE')
		self.assertFalse(Token.objects.filter(device__user=self.user).exists())
		send_code_email.assert_called_once()

	@patch('account.two_factor.send_code_email')
	def test_resend_replaces_previous_challenge(self, send_code_email):
		login_response = self.client.post(
			'/account/api/auth/login/',
			{'username': self.user.username, 'password': 'test-password'},
			format='json',
		)
		original = TwoFactorCode.objects.get(user=self.user)
		resend_response = self.client.post(
			'/account/api/auth/2fa/resend/',
			{'challenge_id': login_response.data['challenge_id']},
			format='json',
		)
		replacement = TwoFactorCode.objects.get(used=False, user=self.user)

		self.assertEqual(resend_response.status_code, 200)
		self.assertTrue(TwoFactorCode.objects.get(pk=original.pk).used)
		self.assertEqual(resend_response.data['challenge_id'], str(replacement.id))
		self.assertEqual(send_code_email.call_count, 2)


class AccountProfileApiTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.client.defaults['HTTP_DARK_TALK_SECRET_KEY'] = (
			f'{settings.DARK_TALK_SECRET_KEY}--test|1'
		)
		self.user = DarkAccount.objects.create_user(
			username='profile-user',
			email='profile@example.com',
			password='test-password',
		)
		device = Device.objects.create(
			user=self.user,
			device_id='profile-device',
			name='Profile device',
			first_ip='127.0.0.1',
			last_ip='127.0.0.1',
		)
		token = Token.objects.create(key='profile-device-token', device=device)
		self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

	def test_authenticated_user_can_update_allowed_profile_fields(self):
		response = self.client.patch(
			'/account/api/profile/',
			{'username': 'renamed-user', 'info': 'About me', 'language': 'English'},
			format='json',
		)

		self.user.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['user']['username'], 'renamed-user')
		self.assertEqual(self.user.info, 'About me')
		self.assertEqual(self.user.language, 'English')

	def test_profile_update_rejects_non_editable_fields(self):
		response = self.client.patch(
			'/account/api/profile/',
			{'email': 'changed@example.com'},
			format='json',
		)

		self.user.refresh_from_db()
		self.assertEqual(response.status_code, 400)
		self.assertEqual(self.user.email, 'profile@example.com')

	def test_user_search_matches_username_without_exposing_email(self):
		DarkAccount.objects.create_user(
			username='another-profile-user',
			email='another@example.com',
			password='test-password',
		)
		response = self.client.get('/account/api/users/search/?username=PROFILE')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			{user['username'] for user in response.data['users']},
			{'profile-user', 'another-profile-user'},
		)
		self.assertNotIn('email', response.data['users'][0])

	def test_user_search_requires_username(self):
		response = self.client.get('/account/api/users/search/')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['message'], 'USERNAME_NOT_PROVIDED')

# Create your tests here.
