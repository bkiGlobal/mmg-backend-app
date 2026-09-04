import io

import pandas as pd
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from core.models import DataExportJob, ExportJobStatus

from .resources import (
    ExpenseDetailResource,
    ExpenseForMaterialResource,
    ExpenseResource,
)


def build_expense_workbook():
    expense = ExpenseResource().export()
    detail = ExpenseDetailResource().export()
    material = ExpenseForMaterialResource().export()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame(expense.dict).to_excel(
            writer, sheet_name='Expense', index=False
        )
        pd.DataFrame(detail.dict).to_excel(
            writer, sheet_name='ExpenseDetail', index=False
        )
        pd.DataFrame(material.dict).to_excel(
            writer, sheet_name='ExpenseForMaterial', index=False
        )
    return buffer.getvalue(), len(expense) + len(detail) + len(material)


@transaction.atomic
def process_export_job(job):
    job = DataExportJob.all_objects.select_for_update().get(pk=job.pk)
    if job.status != ExportJobStatus.QUEUED:
        return job

    job.status = ExportJobStatus.PROCESSING
    job.started_at = timezone.now()
    job.error_message = ''
    job.save(
        update_fields=['status', 'started_at', 'error_message']
    )

    try:
        if job.job_type != 'expense':
            raise ValueError(f'Export type tidak didukung: {job.job_type}')
        content, row_count = build_expense_workbook()
        filename = f'expense_export_{timezone.now():%Y%m%d_%H%M%S}.xlsx'
        job.result_file.save(filename, ContentFile(content), save=False)
        job.row_count = row_count
        job.status = ExportJobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                'result_file',
                'row_count',
                'status',
                'completed_at',
            ]
        )
    except Exception as exc:
        job.status = ExportJobStatus.FAILED
        job.completed_at = timezone.now()
        job.error_message = str(exc)
        job.save(
            update_fields=[
                'status',
                'completed_at',
                'error_message',
            ]
        )
    return job


def process_queued_exports(limit=5):
    jobs = DataExportJob.objects.filter(
        status=ExportJobStatus.QUEUED
    ).order_by('created_at')[:limit]
    return [process_export_job(job) for job in jobs]


def enqueue_export(job_type, requested_by=None, parameters=None):
    """
    Masukkan permintaan export ke antrean.

    Antrean normalnya diproses scheduler melalui
    `manage.py process_export_jobs`. Pada environment tanpa scheduler
    (server lokal / development) setelan EXPORT_JOBS_RUN_INLINE membuat job
    langsung dikerjakan supaya file siap tanpa menunggu cron.
    """
    job = DataExportJob.objects.create(
        job_type=job_type,
        requested_by=requested_by,
        parameters=parameters or {},
    )
    if getattr(settings, 'EXPORT_JOBS_RUN_INLINE', False):
        job = process_export_job(job)
    return job
