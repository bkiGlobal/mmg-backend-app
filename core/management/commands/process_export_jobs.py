from django.core.management.base import BaseCommand

from core.crons import CronJobAlreadyRunning, process_export_queue


class Command(BaseCommand):
    help = 'Proses antrian export admin.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=5)

    def handle(self, *args, **options):
        try:
            jobs = process_export_queue(limit=options['limit'])
        except CronJobAlreadyRunning as exc:
            self.stdout.write(self.style.WARNING(str(exc)))
            return
        self.stdout.write(
            self.style.SUCCESS(f'{len(jobs)} export job diproses.')
        )
