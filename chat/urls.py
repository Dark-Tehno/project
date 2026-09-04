from django.urls import path
from . import views

urlpatterns = [
    path('chats/create/', views.ChatView.as_view(), name='chats_create'),
    path('chats/<int:id>/', views.ChatView.as_view(), name='chats_id'),
]
