import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Salin upload lama dari BASE_DIR ke MEDIA_ROOT tanpa menghapus '
        'file sumber.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Tampilkan rencana tanpa menyalin file.',
        )

    def handle(self, *args, **options):
        destination_root = Path(settings.MEDIA_ROOT).resolve()
        legacy_roots = [
            Path(root).resolve()
            for root in getattr(settings, 'LEGACY_MEDIA_ROOTS', ())
        ]
        directories = getattr(settings, 'LEGACY_MEDIA_DIRECTORIES', ())
        if not legacy_roots or not directories:
            raise CommandError('Konfigurasi legacy media belum tersedia.')

        copied = skipped = 0
        for legacy_root in legacy_roots:
            for directory in directories:
                source_dir = (legacy_root / directory).resolve()
                if not source_dir.is_dir():
                    continue
                for source in source_dir.rglob('*'):
                    if not source.is_file():
                        continue
                    relative_path = source.relative_to(legacy_root)
                    destination = destination_root / relative_path
                    if destination.exists():
                        skipped += 1
                        continue
                    self.stdout.write(
                        f'{source} -> {destination}'
                    )
                    if not options['dry_run']:
                        destination.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        shutil.copy2(source, destination)
                    copied += 1

        action = 'akan disalin' if options['dry_run'] else 'disalin'
        self.stdout.write(
            self.style.SUCCESS(
                f'{copied} file {action}; {skipped} file dilewati.'
            )
        )
