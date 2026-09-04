from datetime import date

from django.core.management.base import BaseCommand, CommandError

from team.holidays import sync_indonesian_holidays, sync_summary_line


class Command(BaseCommand):
    help = (
        'Sinkronkan kalender libur nasional Indonesia ke tabel Holiday. '
        'Tanpa argumen, perintah ini mengambil bulan berjalan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Tahun yang disinkronkan (default: tahun berjalan).',
        )
        parser.add_argument(
            '--month',
            type=int,
            help=(
                'Bulan 1-12. Kosongkan bersama --full-year untuk '
                'mengambil satu tahun penuh.'
            ),
        )
        parser.add_argument(
            '--full-year',
            action='store_true',
            help='Ambil seluruh bulan pada tahun tersebut.',
        )

    def handle(self, *args, **options):
        today = date.today()
        year = options['year'] or today.year
        if options['full_year']:
            month = None
        else:
            month = options['month'] or today.month

        if month is not None and not 1 <= month <= 12:
            raise CommandError('--month harus berada di antara 1 dan 12.')

        summary = sync_indonesian_holidays(year, month)
        self.stdout.write(self.style.SUCCESS(sync_summary_line(summary)))

        for label, key in (
            ('baru', 'created'),
            ('diperbarui', 'updated'),
        ):
            for day, name in summary[key]:
                self.stdout.write(f'  [{label}] {day} · {name}')
