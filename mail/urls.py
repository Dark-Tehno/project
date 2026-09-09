from django.urls import path
from . import views


urlpatterns = [
    path('', views.temp_mail_view, name='temp_mail'),
    path('<str:username>/', views.mail_user_view, name='mail_user'),
    path('webhook/', views.mail_webhook, name='mail_webhook'),
    path('api/extend-email/', views.extend_email_session, name='extend_email_session'),
]