from django.urls import path
from chat.web.views import chat_web_versions, data_js, chat_web_release

urlpatterns = [
    path('', chat_web_versions, name="chat_web_versions"),
    path('release/', chat_web_release, name="chat_web_release"),
    path('data.js', data_js, name="data_js")
]
