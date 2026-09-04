import mimetypes
import posixpath
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import magic
from cryptography.fernet import InvalidToken
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import View
from django_encrypted_filefield.crypt import Cryptographer


class AuthenticatedEncryptedMediaView(LoginRequiredMixin, View):
    """
    Dekripsi media melalui Django storage untuk user yang sudah login.

    FetchView bawaan library menggabungkan MEDIA_ROOT dan path URL dengan
    ``str.replace``. Ketika MEDIA_ROOT tidak memiliki trailing slash, path
    akhirnya menjadi ``.../mediafile`` dan selalu 404. Membaca melalui storage
    juga membuat implementasi ini tetap kompatibel dengan storage non-lokal.
    """

    login_url = reverse_lazy('admin:login')

    @staticmethod
    def _user_can_access(user, storage_name):
        if user.is_superuser:
            return True

        from team.models import Initial, Signature

        return (
            Signature.objects.filter(
                signature=storage_name,
                user__user=user,
            ).exists()
            or Initial.objects.filter(
                initial=storage_name,
                user__user=user,
            ).exists()
        )

    @staticmethod
    def _storage_name(raw_path):
        path = unquote(raw_path or '')
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc:
            path = parsed.path

        media_path = urlsplit(settings.MEDIA_URL).path
        if media_path and path.startswith(media_path):
            path = path[len(media_path):]
        else:
            path = path.lstrip('/')
            media_prefix = media_path.strip('/')
            if media_prefix and path.startswith(f'{media_prefix}/'):
                path = path[len(media_prefix) + 1:]

        normalized = posixpath.normpath(path).lstrip('/')
        pure_path = PurePosixPath(normalized)
        if (
            not normalized
            or normalized == '.'
            or '..' in pure_path.parts
        ):
            raise Http404
        return normalized

    def get(self, request, *args, **kwargs):
        storage_name = self._storage_name(kwargs.get('path'))
        if not self._user_can_access(request.user, storage_name):
            raise Http404
        try:
            with default_storage.open(storage_name, 'rb') as encrypted_file:
                decrypted = Cryptographer.decrypted(encrypted_file.read())
        except (FileNotFoundError, OSError, InvalidToken, ValueError):
            raise Http404 from None

        content_type = (
            magic.Magic(mime=True).from_buffer(decrypted)
            or mimetypes.guess_type(storage_name)[0]
            or 'application/octet-stream'
        )
        response = HttpResponse(decrypted, content_type=content_type)
        response['Cache-Control'] = 'private, no-store'
        response['Content-Disposition'] = (
            f'inline; filename="{PurePosixPath(storage_name).name}"'
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response
