from .views import (
    LoginView,
    RegisterView,
    LogoutView,
    ProfileView,
    LoginHistoryListView,
    DeviceListView,
    DeviceViewSet
)
from django.urls import path


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('login-history/', LoginHistoryListView.as_view(), name='login-history'),
    path('devices/', DeviceListView.as_view(), name='devices-list'),
    path('devices/<uuid:device_id>/', DeviceViewSet.as_view(), name='devices'),
]