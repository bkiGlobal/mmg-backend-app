from datetime import date

from django.core.management.base import BaseCommand, CommandError

from core.crons import CronJobAlreadyRunning, run_daily_operations


class Command(BaseCommand):
    help = 'Jalankan reminder, progress, inventory, dan attendance.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            help='Tanggal proses YYYY-MM-DD (default hari ini).',
        )

    def handle(self, *args, **options):
        target_date = None
        if options['date']:
            try:
                target_date = date.fromisoformat(options['date'])
            except ValueError as exc:
                raise CommandError('Format --date harus YYYY-MM-DD.') from exc
        try:
            counts = run_daily_operations(target_date)
        except CronJobAlreadyRunning as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        summary = ', '.join(
            f'{key}={value}' for key, value in counts.items()
        )
        self.stdout.write(self.style.SUCCESS(summary))
