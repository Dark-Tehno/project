from django.urls import path
from . import views

urlpatterns = [
    path('chats/create/', views.ChatView.as_view(), name='chats_create'),
    path('chats/<int:id>/', views.ChatView.as_view(), name='chats_id'),
    path('chats/', views.ChatsView.as_view(), name='chats'),
    path('chats/<int:id>/messages/', views.ChatMessagesView.as_view(), name='chat_messages'),
    path('chats/<int:id>/participants/', views.ChatParticipantsView.as_view(), name='chat_participants'),
    path('chats/<int:id>/participants/<int:user_id>/', views.ChatParticipantsView.as_view(), name='chat_participant'),
    path('chats/<int:id>/read/', views.ChatReadView.as_view(), name='chat_read'),
    path('chats/blocked/<str:username>/', views.ChatBlockedView.as_view(), name='chat_blocked'),
    path('chats/unblocked/<str:username>/', views.ChatUnBlockedView.as_view(), name='chat_unblocked'),

    path('messages/create/', views.MessagesCreateView.as_view(), name='message_create'),
    path('messages/<int:id>/', views.MessageView.as_view(), name='message_detail'),
    path('messages/read/<int:id>/', views.MessagesReadView.as_view(), name='message_read'),
    path('messages/reaction/<int:id>/', views.MessagesReactionView.as_view(), name='message_reaction'),
]
