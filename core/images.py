import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image, ImageOps, UnidentifiedImageError


def _jpeg_ready(image):
    if image.mode in ('RGBA', 'LA') or (
        image.mode == 'P' and 'transparency' in image.info
    ):
        rgba_image = image.convert('RGBA')
        background = Image.new('RGB', rgba_image.size, 'white')
        background.paste(rgba_image, mask=rgba_image.getchannel('A'))
        return background
    return image.convert('RGB')


def compress_uploaded_image(field_file):
    """
    Kompres upload gambar yang belum disimpan.

    File non-gambar dikembalikan tanpa perubahan sehingga fungsi ini aman
    dipakai untuk FileField yang juga menerima PDF atau dokumen lainnya.
    """
    if not field_file or getattr(field_file, '_committed', True):
        return False

    uploaded_file = field_file.file
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as source:
            source.load()
            image = ImageOps.exif_transpose(source)
            max_width = getattr(
                settings,
                'IMAGE_UPLOAD_MAX_WIDTH',
                1920,
            )
            max_height = getattr(
                settings,
                'IMAGE_UPLOAD_MAX_HEIGHT',
                1920,
            )
            image.thumbnail(
                (max_width, max_height),
                Image.Resampling.LANCZOS,
            )
            image = _jpeg_ready(image)

            output = BytesIO()
            image.save(
                output,
                format='JPEG',
                quality=getattr(
                    settings,
                    'IMAGE_UPLOAD_QUALITY',
                    82,
                ),
                optimize=True,
                progressive=True,
            )
    except (OSError, UnidentifiedImageError, ValueError):
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass
        return False

    original_name = os.path.basename(
        field_file.name or 'image'
    )
    basename, _ = os.path.splitext(original_name)
    compressed = ContentFile(
        output.getvalue(),
        name=f'{basename}.jpg',
    )
    field_file.file = compressed
    field_file.name = compressed.name
    field_file._committed = False
    return True


def compress_instance_images(instance, update_fields=None):
    allowed_fields = (
        set(update_fields) if update_fields is not None else None
    )
    compressed_fields = set()

    for field in instance._meta.concrete_fields:
        if not isinstance(field, models.FileField):
            continue
        if allowed_fields is not None and field.name not in allowed_fields:
            continue
        field_file = getattr(instance, field.name, None)
        if compress_uploaded_image(field_file):
            compressed_fields.add(field.name)

    return compressed_fields
