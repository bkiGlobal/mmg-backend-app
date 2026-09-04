import fcntl
import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from time import monotonic

from django.conf import settings
from django.db import close_old_connections

from core.automation import run_daily_automations
from finance.export_jobs import process_queued_exports


logger = logging.getLogger(__name__)


class CronJobAlreadyRunning(RuntimeError):
    """Raised when the same scheduled job is still running."""


def _lock_directory():
    configured = getattr(settings, 'CRON_LOCK_DIR', None)
    return Path(
        configured
        or Path(tempfile.gettempdir()) / 'mmg_backend_app_cron'
    )


@contextmanager
def cron_job_lock(job_name):
    """Prevent overlapping executions on the same server."""
    lock_directory = _lock_directory()
    lock_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = lock_directory / f'{job_name}.lock'

    with lock_path.open('a+', encoding='utf-8') as lock_file:
        try:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            raise CronJobAlreadyRunning(
                f'Job {job_name} masih berjalan.'
            ) from exc

        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _run_scheduled_job(job_name, callback):
    started_at = monotonic()
    with cron_job_lock(job_name):
        close_old_connections()
        logger.info('Cron job %s dimulai.', job_name)
        try:
            result = callback()
        except Exception:
            logger.exception('Cron job %s gagal.', job_name)
            raise
        finally:
            close_old_connections()

    logger.info(
        'Cron job %s selesai dalam %.2f detik.',
        job_name,
        monotonic() - started_at,
    )
    return result


def run_daily_operations(target_date=None):
    """Run reminders, progress, inventory, and attendance automation."""
    return _run_scheduled_job(
        'daily_operations',
        lambda: run_daily_automations(target_date),
    )


def process_export_queue(limit=10):
    """Process queued admin exports independently from daily automation."""
    return _run_scheduled_job(
        'export_queue',
        lambda: process_queued_exports(limit=limit),
    )
