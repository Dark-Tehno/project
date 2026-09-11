from django.urls import path

from account.api.views import (
    LoginAPIView,
    RegisterAPIView,
    LogoutAPIView,
    ProfileAPIView,
    LoginHistoryListAPIView,
    DeviceListAPIView,
    DeviceAPIViewSet
)
from . import views


urlpatterns = [
    # api:
    path('api/auth/register/', RegisterAPIView.as_view(), name='register'),
    path('api/auth/login/', LoginAPIView.as_view(), name='login'),
    path('api/auth/logout/', LogoutAPIView.as_view(), name='logout'),
    path('api/profile/', ProfileAPIView.as_view(), name='profile'),
    path('api/login-history/', LoginHistoryListAPIView.as_view(), name='login-history'),
    path('api/devices/', DeviceListAPIView.as_view(), name='devices-list'),
    path('api/devices/<uuid:device_id>/', DeviceAPIViewSet.as_view(), name='devices'),

    # views: аутентификация
    path('register/', views.register_view, name='register-view'),
    path('login/', views.login_view, name='login-view'),
    path('login/verify/', views.two_factor_verify_view, name='two-factor-verify'),
    path('login/verify/resend/', views.two_factor_resend, name='two-factor-resend'),
    path('login/verify/cancel/', views.two_factor_cancel, name='two-factor-cancel'),
    path('logout/', views.logout_view, name='logout-view'),

    # views: профиль и аккаунт
    path('', views.profile_view, name='profile-view'),
    path('profile/', views.profile_view, name='profile-view'),
    path('profile/security/', views.security_view, name='security-view'),
    path('profile/security/2fa/', views.toggle_two_factor, name='toggle-two-factor'),
    path('profile/devices/', views.devices_view, name='devices-view'),
    path('profile/devices/<uuid:device_id>/trust/', views.device_toggle_trust, name='device-toggle-trust'),
    path('profile/devices/<uuid:device_id>/block/', views.device_toggle_block, name='device-toggle-block'),
    path('profile/devices/<uuid:device_id>/delete/', views.device_delete, name='device-delete'),
    path('profile/login-history/', views.login_history_view, name='login-history-view'),

    # views: подтверждение почты
    path('email/confirm/', views.email_confirm_view, name='email-confirm'),
    path('email/confirm/resend/', views.email_confirm_resend, name='email-confirm-resend'),

    # views: сброс пароля
    path('password-reset/', views.password_reset_request_view, name='password-reset-request'),
    path('password-reset/confirm/', views.password_reset_confirm_view, name='password-reset-confirm'),
]