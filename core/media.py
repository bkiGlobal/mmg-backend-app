import mimetypes
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404


def _safe_candidate(root, relative_path):
    """Resolve a media path without allowing traversal or symlink escapes."""
    root = Path(root).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def resolve_media_path(path):
    """
    Resolve files from MEDIA_ROOT first, then from allow-listed legacy folders.

    Older installations stored uploads directly below BASE_DIR. The fallback
    keeps those records readable while every new upload continues to use the
    dedicated MEDIA_ROOT.
    """
    relative_path = PurePosixPath(path)
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or '..' in relative_path.parts
    ):
        return None

    primary = _safe_candidate(settings.MEDIA_ROOT, relative_path)
    if primary and primary.is_file():
        return primary

    allowed_directories = set(
        getattr(settings, 'LEGACY_MEDIA_DIRECTORIES', ())
    )
    if relative_path.parts[0] not in allowed_directories:
        return None

    for root in getattr(settings, 'LEGACY_MEDIA_ROOTS', ()):
        candidate = _safe_candidate(root, relative_path)
        if candidate and candidate.is_file():
            return candidate
    return None


def serve_media(request, path):
    """Serve media from the current or allow-listed legacy storage."""
    media_path = resolve_media_path(path)
    if media_path is None:
        raise Http404('Media tidak ditemukan.')

    content_type, encoding = mimetypes.guess_type(media_path.name)
    response = FileResponse(
        media_path.open('rb'),
        content_type=content_type or 'application/octet-stream',
        filename=media_path.name,
    )
    if encoding:
        response.headers['Content-Encoding'] = encoding
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@staff_member_required(login_url='admin:login')
def serve_staff_media(request, path):
    """Serve sensitive uploads only to authenticated, active admin staff."""
    return serve_media(request, path)
