from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView

from account.models import DarkAccount
from chat.models import ChatParticipant, Message, Chat


class SecureMediaView(APIView):

    def get(self, request, file_path):

        full_path = (settings.MEDIA_ROOT / file_path).resolve()

        if not str(full_path).startswith(str(settings.MEDIA_ROOT.resolve())):
            raise Http404

        if not full_path.exists():
            raise Http404

        # --------------------
        # DEFAULTS
        # --------------------

        if file_path.startswith("defaults/"):
            return FileResponse(open(full_path, "rb"))

        # --------------------
        # PUBLIC
        # --------------------

        if file_path.startswith("public/"):
            return FileResponse(open(full_path, "rb"))

        # Всё остальное требует авторизации

        if request.user is None:
            raise Http404

        # --------------------
        # USER AVATARS
        # --------------------

        if file_path.startswith("avatars/"):

            try:
                _, username, _ = file_path.split("/", 2)
            except ValueError:
                raise Http404

            try:
                owner = DarkAccount.objects.get(username=username)
            except DarkAccount.DoesNotExist:
                raise Http404

            if owner.avatar_access == DarkAccount.AccessChoices.ALL:
                return FileResponse(open(full_path, "rb"))

            if owner.avatar_access == DarkAccount.AccessChoices.AUTHENTICATED:
                return FileResponse(open(full_path, "rb"))

            if owner == request.user:
                return FileResponse(open(full_path, "rb"))

            raise Http404

        # --------------------
        # CHAT AVATARS
        # --------------------

        if file_path.startswith("chat_avatars/"):

            chat = (
                Chat.objects
                .filter(avatar=file_path)
                .first()
            )

            if not chat:
                raise Http404

            if ChatParticipant.objects.filter(
                chat=chat,
                user=request.user,
                left_at__isnull=True,
            ).exists():
                return FileResponse(open(full_path, "rb"))

            raise Http404

        # --------------------
        # CHAT FILES
        # --------------------

        if file_path.startswith("chat_files/"):

            message = (
                Message.objects
                .select_related("chat")
                .filter(attachment=file_path)
                .first()
            )

            if not message:
                raise Http404

            if ChatParticipant.objects.filter(
                chat=message.chat,
                user=request.user,
                left_at__isnull=True,
            ).exists():
                return FileResponse(open(full_path, "rb"))

            raise Http404

        # --------------------
        # VERSION FILES
        # --------------------

        if file_path.startswith("file_version/"):
            return FileResponse(open(full_path, "rb"))

        if file_path.startswith("image_version/"):
            return FileResponse(open(full_path, "rb"))

        raise Http404