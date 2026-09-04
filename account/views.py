from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DarkAccount, LoginHistory, Device, Version, Token
from .serializers import (
    DarkAccountSerializer,
    DeviceSerializer,
    DeviceUpdateSerializer,
    LoginHistorySerializer
)
from .utils import get_or_create_device, get_client_ip_address, StandartAPIPermission


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Создаёт пользователя и АВТОМАТИЧЕСКИ создаёт запись Device со всей
    доступной информацией (IP, User-Agent, ОС, браузер, тип устройства
    и т.д. — парсятся сервером сами). Клиент ничего для этого делать
    не обязан; при желании может передать блок "device" с уточнениями.
    """
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

class LoginView(APIView):
    """POST /api/auth/login/"""
    permission_classes = [StandartAPIPermission]

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
            "application_version": application_version
        }

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


class LogoutView(APIView):
    permission_classes = [StandartAPIPermission]

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


class ProfileView(APIView):
    permission_classes = [StandartAPIPermission]

    def get(self, request):
        return Response(
                    {
                        'status': 'success',
                        'user': DarkAccountSerializer(request.user).data,
                    },
                    status=status.HTTP_200_OK
                )


class DeviceViewSet(APIView):
    """
    GET    /api/devices/{id}/      — детали устройства
    PATCH  /api/devices/{id}/      — переименовать / пометить доверенным
    DELETE /api/devices/{id}/      — удалить устройство (разлогинить его)
    """
    permission_classes = [StandartAPIPermission]

    def get(self, request, device_id):
        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return Response({'status': 'error', 'message': 'DEVICE_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'status': 'success',
            "device": DeviceSerializer(device).data
        })

    def patch(self, request, device_id):
        try:
            device = Device.objects.get(device_id=device_id)
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
            Device.objects.delete(device_id=device_id)
            return Response({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)
        except Device.DoesNotExist:
            return Response({'status': 'error', 'message': 'DEVICE_NOT_FOUND'}, status=status.HTTP_404_NOT_FOUND)


class DeviceListView(APIView):
    permission_classes = [StandartAPIPermission]

    def get(self, request):
        devices = Device.objects.filter(user=request.user)

        return Response({
            'status': 'success',
            "devices": DeviceSerializer(devices, many=True).data
        })


class LoginHistoryListView(APIView):
    permission_classes = [StandartAPIPermission]

    def get(self, request):
        login_history = LoginHistory.objects.filter(user=self.request.user).select_related('device')
        return Response({
            'status': 'success',
            'login_history': LoginHistorySerializer(login_history, many=True).data,
        })