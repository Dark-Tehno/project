from pathlib import Path
import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from account.models import DarkAccount
from chat.models import ChatParticipant, Message, Chat


class SecureMediaView(APIView):
    permission_classes = [AllowAny]

    @staticmethod
    def _serve_file(request, full_path):
        file_size = full_path.stat().st_size
        content_type = mimetypes.guess_type(full_path.name)[0] or 'application/octet-stream'
        range_header = request.headers.get('Range')

        if not range_header:
            response = FileResponse(open(full_path, 'rb'), content_type=content_type)
            response['Content-Length'] = str(file_size)
            response['Accept-Ranges'] = 'bytes'
            return response

        if not range_header.startswith('bytes=') or ',' in range_header:
            return HttpResponse(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        range_value = range_header[6:].strip()
        try:
            start_text, end_text = range_value.split('-', 1)
            if start_text:
                start = int(start_text)
                end = int(end_text) if end_text else file_size - 1
            else:
                suffix_length = int(end_text)
                start = max(file_size - suffix_length, 0)
                end = file_size - 1
        except (TypeError, ValueError):
            return HttpResponse(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        if start < 0 or start >= file_size or end < start:
            return HttpResponse(status=416, headers={'Content-Range': f'bytes */{file_size}'})

        end = min(end, file_size - 1)
        content_length = end - start + 1
        media_file = open(full_path, 'rb')
        media_file.seek(start)

        def stream_range():
            remaining = content_length
            try:
                while remaining:
                    chunk = media_file.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
            finally:
                media_file.close()

        response = StreamingHttpResponse(stream_range(), status=206, content_type=content_type)
        response['Content-Length'] = str(content_length)
        response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        return response

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
        # STLM
        # --------------------

        if file_path.startswith("stlm/"):
            return self._serve_file(request, full_path)

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