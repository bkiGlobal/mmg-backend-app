"""
Sinkronisasi kalender libur nasional Indonesia ke tabel Holiday.

Sumber data adalah paket `holidays`, yang menghitung sendiri kalender
Hijriah dan Saka sehingga Idul Fitri, Idul Adha, Nyepi, Waisak, dan Imlek
ikut terbawa. Perhitungan dilakukan offline supaya sinkronisasi tetap
berjalan pada server tanpa akses internet.

Aturan penggabungan dibuat agar sinkronisasi tidak pernah menimpa keputusan
manusia:

* entri manual (`HolidaySource.MANUAL`) tidak pernah disentuh, sehingga cuti
  bersama yang ditetapkan perusahaan tetap aman;
* entri nasional yang sudah dihapus dianggap sengaja dicoret dan tidak
  dihidupkan kembali;
* entri nasional yang masih aktif hanya diperbarui ketika namanya berubah.
"""

from calendar import monthrange
from datetime import date

import holidays as holidays_library
from django.db import transaction

from .models import Holiday, HolidaySource


COUNTRY_CODE = 'ID'
LANGUAGE = 'id'


def fetch_indonesian_holidays(year, month=None):
    """
    Kembalikan daftar `(tanggal, nama)` libur nasional yang terurut.

    Ketika `month` diisi, hanya libur pada bulan tersebut yang dikembalikan.
    """
    calendar = holidays_library.country_holidays(
        COUNTRY_CODE,
        years=year,
        language=LANGUAGE,
    )
    entries = sorted(calendar.items())
    if month:
        entries = [entry for entry in entries if entry[0].month == month]
    return entries


def month_bounds(year, month):
    """Kembalikan tanggal pertama dan terakhir pada satu bulan."""
    return (
        date(year, month, 1),
        date(year, month, monthrange(year, month)[1]),
    )


@transaction.atomic
def sync_indonesian_holidays(year, month=None):
    """
    Simpan libur nasional Indonesia ke tabel Holiday.

    Mengembalikan ringkasan berisi jumlah entri yang dibuat, diperbarui, dan
    dilewati beserta alasannya.
    """
    summary = {
        'year': year,
        'month': month,
        'created': [],
        'updated': [],
        'skipped_manual': [],
        'skipped_deleted': [],
        'unchanged': [],
    }

    for day, name in fetch_indonesian_holidays(year, month):
        existing = Holiday.all_objects.filter(date=day).first()

        if existing is None:
            Holiday.objects.create(
                date=day,
                name=name,
                source=HolidaySource.NATIONAL,
            )
            summary['created'].append((day, name))
            continue

        if existing.is_deleted:
            # Penghapusan diperlakukan sebagai keputusan sadar operator.
            summary['skipped_deleted'].append((day, existing.name))
            continue

        if existing.source == HolidaySource.MANUAL:
            summary['skipped_manual'].append((day, existing.name))
            continue

        if existing.name != name:
            existing.name = name
            existing.save(update_fields=['name'])
            summary['updated'].append((day, name))
            continue

        summary['unchanged'].append((day, name))

    return summary


def sync_summary_line(summary):
    """Ringkas hasil sinkronisasi menjadi satu baris yang mudah dibaca."""
    scope = f"{summary['year']}"
    if summary['month']:
        scope = f"{scope}-{summary['month']:02d}"
    return (
        f"{scope}: {len(summary['created'])} baru, "
        f"{len(summary['updated'])} diperbarui, "
        f"{len(summary['unchanged'])} tetap, "
        f"{len(summary['skipped_manual'])} manual dilewati, "
        f"{len(summary['skipped_deleted'])} terhapus dilewati."
    )
