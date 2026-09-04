"""Storage backend untuk file statis."""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):
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
