from django.contrib import admin
from .models import (Chat,
    ChatParticipant,
    Message,
    MessageRead,
    MessageReaction
    )
# Register your models here.
admin.site.register(Chat)
admin.site.register(ChatParticipant)
admin.site.register(Message)
admin.site.register(MessageRead)
admin.site.register(MessageReaction)
