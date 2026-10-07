from uuid import UUID

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from account.models import DarkAccount, LoginHistory, Device, Version, Token, TwoFactorCode
from account.api.serializers import (
    DarkAccountSerializer,
    AccountUpdateSerializer,
    DeviceSerializer,
    DeviceUpdateSerializer,
    LoginHistorySerializer,
    UserSearchSerializer,
)
from account.utils import DeviceTokenAuthentication, get_or_create_device, get_client_ip_address, StandartAPIPermission
from account.two_factor import issue_two_factor_code


class RegisterAPIView(APIView):
    """
    POST /api/auth/register/

    Создаёт пользователя и АВТОМАТИЧЕСКИ создаёт запись Device со всей
    доступной информацией (IP, User-Agent, ОС, браузер, тип устройства
    и т.д. — парсятся сервером сами). Клиент ничего для этого делать
    не обязан; при желании может передать блок "device" с уточнениями.
    """
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]
    
    def post(self, request):
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        username = request.data.get('username', email.split("@")[0] if email else None)
        language = request.data.get('language', 'Russian')
        date_of_birth = request.data.get('date_of_birth', None)
        # device:
        device_id = request.data.get('device_id', None)
        application = request.app_version.split('|')[0]
        application_version = request.app_version.split('|')[1]

        if email is None or password is None:
            return Response({'status': 'error', 'message': 'EMAIL_PASSWORD_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

        if language != "Russian" and language != "English":
            return Response({'status': 'error', 'message': 'LANGUAGE_NOT_SUPPORTED'}, status=status.HTTP_400_BAD_REQUEST)

        user = DarkAccount.objects.create_user(
            username=username,
            email=email,
            password=password,
            language=language,
            date_of_birth=date_of_birth
        )

        device_extra = {
            "device_id": device_id,
            "application": application,
            "application_version": application_version
        }

        device = get_or_create_device(request, user, extra_data=device_extra)

        version = Version.objects.filter(application=application, version=application_version).first()
        device.app_version = version
        device.save()

        LoginHistory.objects.create(
            user=user,
            device=device,
            ip=get_client_ip_address(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            country=device.country,
            city=device.city,
            status=LoginHistory.Status.SUCCESS,
            reason='Регистрация',
        )

        token, _ = Token.objects.get_or_create(device=device)
        user.last_online = timezone.now()
        user.save(update_fields=['last_online'])

        return Response(
            {
                'status': 'success',
                'token': token.key,
                'user': DarkAccountSerializer(user).data,
                'device': DeviceSerializer(device).data,
            },
            status=status.HTTP_201_CREATED,
        )

class LoginAPIView(APIView):
    """POST /api/auth/login/"""
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        username = request.data.get("username", None)
        password = request.data.get("password", None)
        device_id = request.data.get('device_id', None)
        application = request.app_version.split('|')[0]
        application_version = request.app_version.split('|')[1]

        if username is None or password is None:
            return Response({'status': 'error', 'message': 'USERNAME_PASSWORD_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'status': 'error', 'message': 'INVALID_CREDENTIALS'}, status=status.HTTP_401_UNAUTHORIZED)

        device_extra = {
            "device_id": device_id,
            "application": application,
            "application_version": application_version,
        }

        if user.two_factor_enabled:
            existing_device = None
            existing_device_id = device_id or request.META.get('HTTP_X_DEVICE_ID')
            if existing_device_id:
                existing_device = Device.objects.filter(
                    user=user,
                    device_id=existing_device_id,
                ).first()
            if existing_device and existing_device.blocked:
                LoginHistory.objects.create(
                    user=user,
                    device=existing_device,
                    ip=get_client_ip_address(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    country=existing_device.country,
                    city=existing_device.city,
                    status=LoginHistory.Status.BLOCKED,
                    reason='Устройство заблокировано',
                )
                return Response(
                    {'status': 'error', 'detail': 'Это устройство заблокировано.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not user.email:
                return Response(
                    {'status': 'error', 'message': 'TWO_FACTOR_EMAIL_NOT_CONFIGURED'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            challenge = issue_two_factor_code(user)
            return Response(
                {
                    'status': 'two_factor_required',
                    'challenge_id': str(challenge.id),
                    'expires_at': challenge.expires_at,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        device = get_or_create_device(request, user, extra_data=device_extra)

        if device.blocked:
            LoginHistory.objects.create(
                user=user,
                device=device,
                ip=get_client_ip_address(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                country=device.country,
                city=device.city,
                status=LoginHistory.Status.BLOCKED,
                reason='Устройство заблокировано',
            )
            return Response({'status': 'error', 'detail': 'Это устройство заблокировано.'}, status=status.HTTP_403_FORBIDDEN)

        LoginHistory.objects.create(
            user=user,
            device=device,
            ip=get_client_ip_address(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            country=device.country,
            city=device.city,
            status=LoginHistory.Status.SUCCESS,
            reason='Вход выполнен',
        )

        token, _ = Token.objects.get_or_create(device=device)
        user.last_online = timezone.now()
        user.save(update_fields=['last_online'])

        return Response(
            {
                'status': 'success',
                'token': token.key,
                'user': DarkAccountSerializer(user).data,
                'device': DeviceSerializer(device).data,
            }
        )


class TwoFactorSettingsAPIView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]

    def get(self, request):
        return Response({
            'status': 'success',
            'two_factor_enabled': request.user.two_factor_enabled,
        })

    def patch(self, request):
        enabled = request.data.get('enabled')
        if not isinstance(enabled, bool):
            return Response(
                {'status': 'error', 'message': 'INVALID_TWO_FACTOR_ENABLED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if enabled and not request.user.email:
            return Response(
                {'status': 'error', 'message': 'TWO_FACTOR_EMAIL_NOT_CONFIGURED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.two_factor_enabled != enabled:
            now = timezone.now()
            request.user.two_factor_enabled = enabled
            request.user.save(update_fields=['two_factor_enabled'])
            TwoFactorCode.objects.filter(user=request.user, used=False).update(
                used=True,
                used_at=now,
            )

        return Response({
            'status': 'success',
            'two_factor_enabled': request.user.two_factor_enabled,
        })


class TwoFactorVerifyAPIView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'two_factor'

    def post(self, request):
        challenge_id = request.data.get('challenge_id')
        code = request.data.get('code')
        if not challenge_id or not isinstance(code, str):
            return Response(
                {'status': 'error', 'message': 'CHALLENGE_CODE_NOT_PROVIDED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            challenge_id = UUID(str(challenge_id))
        except (TypeError, ValueError, AttributeError):
            return Response(
                {'status': 'error', 'message': 'INVALID_OR_EXPIRED_TWO_FACTOR_CODE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        with transaction.atomic():
            challenge = (
                TwoFactorCode.objects.select_for_update()
                .select_related('user')
                .filter(
                    id=challenge_id,
                    used=False,
                    expires_at__gte=now,
                    user__is_active=True,
                    user__two_factor_enabled=True,
                )
                .first()
            )
            if challenge is None:
                return Response(
                    {'status': 'error', 'message': 'INVALID_OR_EXPIRED_TWO_FACTOR_CODE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not constant_time_compare(challenge.code, code.strip()):
                LoginHistory.objects.create(
                    user=challenge.user,
                    ip=get_client_ip_address(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    status=LoginHistory.Status.FAILED,
                    reason='Неверный код 2FA через API',
                )
                return Response(
                    {'status': 'error', 'message': 'INVALID_OR_EXPIRED_TWO_FACTOR_CODE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            device_id = request.data.get('device_id')
            if device_id is not None and (
                not isinstance(device_id, str) or not device_id or len(device_id) > 255
            ):
                return Response(
                    {'status': 'error', 'message': 'INVALID_DEVICE_ID'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application, application_version = request.app_version.split('|', 1)
            device = get_or_create_device(
                request,
                challenge.user,
                extra_data={
                    'device_id': device_id,
                    'application': application,
                    'application_version': application_version,
                },
            )
            if device.blocked:
                LoginHistory.objects.create(
                    user=challenge.user,
                    device=device,
                    ip=get_client_ip_address(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    country=device.country,
                    city=device.city,
                    status=LoginHistory.Status.BLOCKED,
                    reason='Устройство заблокировано',
                )
                return Response(
                    {'status': 'error', 'detail': 'Это устройство заблокировано.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            challenge.used = True
            challenge.used_at = now
            challenge.save(update_fields=['used', 'used_at'])
            token, _ = Token.objects.get_or_create(device=device)
            LoginHistory.objects.create(
                user=challenge.user,
                device=device,
                ip=get_client_ip_address(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                country=device.country,
                city=device.city,
                status=LoginHistory.Status.SUCCESS,
                reason='Вход подтверждён кодом 2FA',
            )
            challenge.user.last_online = now
            challenge.user.save(update_fields=['last_online'])

        return Response(
            {
                'status': 'success',
                'token': token.key,
                'user': DarkAccountSerializer(challenge.user).data,
                'device': DeviceSerializer(device).data,
            },
            status=status.HTTP_200_OK,
        )


class TwoFactorResendAPIView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'two_factor'

    def post(self, request):
        challenge_id = request.data.get('challenge_id')
        try:
            challenge_id = UUID(str(challenge_id))
        except (TypeError, ValueError, AttributeError):
            return Response(
                {'status': 'error', 'message': 'INVALID_OR_EXPIRED_TWO_FACTOR_CHALLENGE'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        with transaction.atomic():
            challenge = (
                TwoFactorCode.objects.select_for_update()
                .select_related('user')
                .filter(
                    id=challenge_id,
                    used=False,
                    expires_at__gte=now,
                    user__is_active=True,
                    user__two_factor_enabled=True,
                )
                .first()
            )
            if challenge is None:
                return Response(
                    {'status': 'error', 'message': 'INVALID_OR_EXPIRED_TWO_FACTOR_CHALLENGE'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not challenge.user.email:
                return Response(
                    {'status': 'error', 'message': 'TWO_FACTOR_EMAIL_NOT_CONFIGURED'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            challenge.used = True
            challenge.used_at = now
            challenge.save(update_fields=['used', 'used_at'])
            replacement = issue_two_factor_code(challenge.user)

        return Response(
            {
                'status': 'two_factor_required',
                'challenge_id': str(replacement.id),
                'expires_at': replacement.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def post(self, request):
        device_id = request.data.get('device_id', None)
        if device_id is None:
            return Response({'status': 'error', 'message': 'DEVICE_ID_NOT_PROVIDED'}, status=status.HTTP_400_BAD_REQUEST)

        device = Device.objects.filter(user=request.user, device_id=device_id).first()

        LoginHistory.objects.create(
            user=request.user,
            device=device,
            ip=get_client_ip_address(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            country=device.country,
            city=device.city,
            status=LoginHistory.Status.SUCCESS,
            reason='Выход из аккаунта',
        )
        
        request.user.is_online = False
        request.user.last_online = timezone.now()
        request.user.save(update_fields=['is_online', 'last_online'])

        Token.objects.filter(device=device).delete()

        return Response({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)


class ProfileAPIView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [StandartAPIPermission]

    def get(self, request):
        return Response(
                    {
                        'status': 'success',
                        'user': DarkAccountSerializer(request.user).data,
                    },
                    status=status.HTTP_200_OK
                )

    def patch(self, request):
        serializer = AccountUpdateSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(
            {
                'status': 'success',
                'user': DarkAccountSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class UserSearchAPIView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request):
        username = request.query_params.get('username', '').strip()
        if not username:
            return Response(
                {'status': 'error', 'message': 'USERNAME_NOT_PROVIDED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        users = DarkAccount.objects.filter(
            username__icontains=username,
            is_active=True,
        ).order_by('username')[:20]
        return Response({
            'status': 'success',
            'users': UserSearchSerializer(users, many=True).data,
        }, status=status.HTTP_200_OK)


class DeviceAPIViewSet(APIView):
    """
    GET    /api/devices/{id}/      — детали устройства
    PATCH  /api/devices/{id}/      — переименовать / пометить доверенным
    DELETE /api/devices/{id}/      — удалить устройство (разлогинить его)
    """
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request, device_id):
        try:
            device = Device.objects.get(user=request.user, device_id=device_id)
        except Device.DoesNotExist:
            return Response({'status': 'error', 'message': 'DEVICE_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'status': 'success',
            "device": DeviceSerializer(device).data
        })

    def patch(self, request, device_id):
        try:
            device = Device.objects.get(user=request.user, device_id=device_id)
        except Device.DoesNotExist:
            return Response({'status': 'error', 'message': 'DEVICE_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeviceUpdateSerializer(device, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                "device": DeviceSerializer(device).data
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, device_id):
        try:
            device = Device.objects.get(user=request.user, device_id=device_id)
        except Device.DoesNotExist:
            return Response({'status': 'error', 'message': 'DEVICE_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)
        Token.objects.filter(device=device).delete()
        device.delete()
        return Response({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)


class DeviceListAPIView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request):
        devices = Device.objects.filter(user=request.user)

        return Response({
            'status': 'success',
            "devices": DeviceSerializer(devices, many=True).data
        })


class LoginHistoryListAPIView(APIView):
    permission_classes = [StandartAPIPermission]
    authentication_classes = [DeviceTokenAuthentication]

    def get(self, request):
        login_history = LoginHistory.objects.filter(user=self.request.user).select_related('device')
        return Response({
            'status': 'success',
            'login_history': LoginHistorySerializer(login_history, many=True).data,
        })