from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/mail/(?P<email_id>\d+)/$', consumers.EmailConsumer.as_asgi()),
]