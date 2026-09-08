from django.urls import path
from . import views

urlpatterns = [
    path('chats/create/', views.ChatView.as_view(), name='chats_create'),
    path('chats/<int:id>/', views.ChatView.as_view(), name='chats_id'),
    path('chats/', views.ChatsView.as_view(), name='chats'),

    # path('messages/create/', views.MessagesView.as_view(), name='chats'),
]
