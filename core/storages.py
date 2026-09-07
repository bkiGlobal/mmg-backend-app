"""Storage backend untuk file statis."""

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(
    CompressedManifestStaticFilesStorage
):
    """
    Manifest storage yang tidak menggagalkan request ketika manifest kosong.

    Penamaan berbasis hash isi dipakai agar perubahan CSS atau JS langsung
    membatalkan cache browser; tanpa itu pengguna bisa terus melihat
    stylesheet lama setelah deploy.

    `manifest_strict` dimatikan supaya berkas yang belum terdaftar pada
    manifest dikembalikan dengan nama aslinya alih-alih melempar
    ValueError. Itu penting pada clone baru atau CI, di mana `manage.py test`
    kerap dijalankan sebelum `collectstatic` pernah dieksekusi.
    """

    manifest_strict = False

    def __init__(self, *args, **kwargs):
        # FILE_UPLOAD_* sengaja privat (0640/0750) untuk media pengguna,
        # sedangkan berkas static harus dapat dibaca oleh proses WhiteNoise.
        kwargs.setdefault('file_permissions_mode', 0o644)
        kwargs.setdefault('directory_permissions_mode', 0o755)
        super().__init__(*args, **kwargs)
