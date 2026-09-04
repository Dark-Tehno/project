from rest_framework import serializers

from .models import DarkAccount, Device, LoginHistory


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = (
            'id', 'user', 'device_id', 'name', 'device_type', 'operating_system',
            'system_version', 'browser', 'browser_version', 'application',
            'application_version', 'first_ip', 'last_ip', 'country', 'city',
            'timezone', 'trusted', 'blocked', 'created_at', 'last_seen',
        )
        read_only_fields = fields


class DeviceUpdateSerializer(serializers.ModelSerializer):
    """Пользователю доступно только переименовать устройство или пометить его доверенным."""

    class Meta:
        model = Device
        fields = ('name', 'trusted')


class DarkAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = DarkAccount
        fields = (
            'id', 'username', 'email', 'avatar', 'info', 'date_of_birth',
            'language', 'is_online', 'last_online', 'email_confirmed',
            'two_factor_enabled', 'date_joined',
        )
        read_only_fields = ('id', 'email', 'is_online', 'last_online', 'email_confirmed', 'date_joined')


class LoginHistorySerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True, default='')

    class Meta:
        model = LoginHistory
        fields = ('id', 'device', 'device_name', 'ip', 'country', 'city', 'status', 'reason', 'created_at')