from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from django.core.files.storage import default_storage
from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from .models import ProjectStatus


IMAGE_EXTENSIONS = {
    '.avif',
    '.gif',
    '.jpeg',
    '.jpg',
    '.png',
    '.webp',
}

STATUS_TONES = {
    ProjectStatus.ON_GOING: 'active',
    ProjectStatus.COMPLETED: 'success',
    ProjectStatus.ON_HOLD: 'warning',
    ProjectStatus.CANCELLED: 'neutral',
    ProjectStatus.DELAYED: 'danger',
    ProjectStatus.TENDER: 'info',
}

DOCUMENT_STATUS_TONES = {
    'approved': 'success',
    'finalized': 'success',
    'in_review': 'warning',
    'rejected': 'danger',
    'draft': 'neutral',
    'archived': 'neutral',
}


def _storage_url(file_name):
    if not file_name:
        return ''
    try:
        return default_storage.url(str(file_name))
    except (NotImplementedError, TypeError, ValueError):
        return ''


def _filtered_admin_url(
    url_name,
    project_id,
    lookup='project__id__exact',
):
    return '{}?{}'.format(
        reverse(url_name),
        urlencode({lookup: project_id}),
    )


def _field_file_url(field_file):
    if not field_file:
        return ''
    try:
        return field_file.url
    except (NotImplementedError, TypeError, ValueError):
        return ''


def _recent_project_documents(project, limit=4):
    items = []
    drawings = list(
        project.project_drawings.filter(is_deleted=False)
        .select_related('drawing_type')
        .order_by('-updated_at')[:limit]
    )
    drawing_names = {
        drawing.document_name
        for drawing in drawings
    }
    documents = list(
        project.project_documents.filter(is_deleted=False)
        .exclude(document_name__in=drawing_names)
        .select_related('document_type')
        .order_by('-updated_at')[:limit]
    )
    sources = (
        (
            documents,
            'Dokumen',
            'description',
            'versions',
            'document_file',
            'admin:project_document_change',
        ),
        (
            drawings,
            'Drawing',
            'architecture',
            'drawing_versions',
            'drawing_file',
            'admin:project_drawing_change',
        ),
    )

    for (
        queryset,
        kind,
        icon,
        version_relation,
        file_field,
        admin_url_name,
    ) in sources:
        for document in queryset:
            version = (
                getattr(document, version_relation)
                .filter(is_deleted=False)
                .order_by('-updated_at', '-created_at')
                .first()
            )
            updated_at = (
                version.updated_at if version else document.updated_at
            )
            status = version.status if version else document.status
            items.append(
                {
                    'kind': kind,
                    'icon': icon,
                    'name': document.document_name,
                    'number': (
                        version.document_number if version else '—'
                    ),
                    'status': status,
                    'status_label': (
                        version.get_status_display()
                        if version
                        else document.get_status_display()
                    ),
                    'status_tone': DOCUMENT_STATUS_TONES.get(
                        status,
                        'neutral',
                    ),
                    'updated_at': updated_at,
                    'file_url': (
                        _field_file_url(getattr(version, file_field))
                        if version
                        else ''
                    ),
                    'change_url': reverse(
                        admin_url_name,
                        args=(document.pk,),
                    ),
                }
            )

    return sorted(
        items,
        key=lambda item: item['updated_at'],
        reverse=True,
    )[:limit]


def _motivation(progress):
    if progress >= 100:
        return 'Selesai dengan bangga. Saatnya merayakan hasil kerja tim.'
    if progress >= 75:
        return 'Garis akhir semakin dekat. Jaga kualitas di setiap detail.'
    if progress >= 50:
        return 'Momentum sudah terbentuk. Kolaborasi tim membuatnya nyata.'
    if progress >= 25:
        return 'Fondasi yang kuat sedang tumbuh menjadi hasil yang terlihat.'
    return 'Setiap proyek besar dimulai dari langkah pertama yang terukur.'


def build_project_showcase(
    project,
    today=None,
    include_recent_documents=False,
):
    today = today or timezone.localdate()
    progress = float(project.progress or 0)
    start_date = project.start_date
    end_date = project.end_date

    calendar_progress = 0
    pace_label = 'Timeline belum lengkap'
    if start_date and end_date:
        total_days = max((end_date - start_date).days, 1)
        elapsed_days = (today - start_date).days
        calendar_progress = min(
            100,
            max(0, round((elapsed_days / total_days) * 100)),
        )
        pace_delta = progress - calendar_progress
        if progress >= 100:
            pace_label = 'Target tercapai'
        elif pace_delta >= 5:
            pace_label = f'{abs(pace_delta):.0f}% di depan timeline'
        elif pace_delta <= -5:
            pace_label = f'{abs(pace_delta):.0f}% di bawah timeline'
        else:
            pace_label = 'Selaras dengan timeline'

    if end_date is None:
        deadline_label = 'Target selesai belum ditentukan'
        deadline_tone = 'neutral'
    else:
        remaining_days = (end_date - today).days
        if remaining_days < 0 and progress < 100:
            deadline_label = f'Terlambat {abs(remaining_days)} hari'
            deadline_tone = 'danger'
        elif remaining_days == 0:
            deadline_label = 'Target selesai hari ini'
            deadline_tone = 'warning'
        elif progress >= 100:
            deadline_label = 'Proyek telah selesai'
            deadline_tone = 'success'
        else:
            deadline_label = f'{remaining_days} hari menuju target'
            deadline_tone = 'active'

    presentation_url = ''
    if project.presentation_image:
        try:
            presentation_url = project.presentation_image.url
        except ValueError:
            presentation_url = ''

    drawing_name = getattr(project, 'latest_drawing_file', '') or ''
    drawing_url = _storage_url(drawing_name)
    drawing_is_image = (
        Path(str(drawing_name)).suffix.lower() in IMAGE_EXTENSIONS
    )
    preview_url = presentation_url or (
        drawing_url if drawing_is_image else ''
    )

    documents_total = getattr(project, 'documents_total', 0)
    documents_approved = getattr(project, 'documents_approved', 0)
    drawings_total = getattr(project, 'drawings_total', 0)
    drawings_approved = getattr(project, 'drawings_approved', 0)
    open_defects = getattr(project, 'open_defects', 0)
    overdue_schedules = getattr(project, 'overdue_schedules', 0)
    team_members = getattr(project, 'team_members_total', 0)

    return {
        'project': project,
        'progress': progress,
        'progress_label': f'{progress:.0f}%',
        'calendar_progress': calendar_progress,
        'pace_label': pace_label,
        'deadline_label': deadline_label,
        'deadline_tone': deadline_tone,
        'status_label': project.get_project_status_display(),
        'status_tone': STATUS_TONES.get(
            project.project_status,
            'neutral',
        ),
        'preview_url': preview_url,
        'drawing_url': drawing_url,
        'has_custom_image': bool(presentation_url),
        'latest_report_date': getattr(
            project,
            'latest_report_date',
            None,
        ),
        'motivation': _motivation(progress),
        'client_name': (
            project.client.full_name if project.client else 'Belum ditentukan'
        ),
        'team_name': (
            project.team.name if project.team else 'Belum ditentukan'
        ),
        'location_name': (
            project.location.name if project.location else 'Belum ditentukan'
        ),
        'documents_total': documents_total,
        'documents_approved': documents_approved,
        'drawings_total': drawings_total,
        'drawings_approved': drawings_approved,
        'open_defects': open_defects,
        'overdue_schedules': overdue_schedules,
        'attention_total': open_defects + overdue_schedules,
        'team_members_total': team_members,
        'change_url': reverse(
            'admin:project_project_change',
            args=(project.pk,),
        ),
        'presentation_url': reverse(
            'admin:project_project_presentation',
            args=(project.pk,),
        ),
        'documents_url': _filtered_admin_url(
            'admin:project_document_changelist',
            project.pk,
        ),
        'drawings_url': _filtered_admin_url(
            'admin:project_drawing_changelist',
            project.pk,
        ),
        'schedules_url': _filtered_admin_url(
            'admin:project_schedule_changelist',
            project.pk,
            'boq_item__project__id__exact',
        ),
        'reports_url': _filtered_admin_url(
            'admin:project_progressreport_changelist',
            project.pk,
            'boq_item__project__id__exact',
        ),
        'recent_documents': (
            _recent_project_documents(project)
            if include_recent_documents
            else []
        ),
    }


def build_showcase_summary(queryset, today=None):
    today = today or timezone.localdate()
    next_month = today + timedelta(days=30)
    summary = queryset.aggregate(
        total=Count('pk'),
        average_progress=Coalesce(
            Avg('progress'),
            Decimal('0'),
        ),
        active=Count(
            'pk',
            filter=Q(
                project_status__in=(
                    ProjectStatus.ON_GOING,
                    ProjectStatus.DELAYED,
                ),
            ),
        ),
        completed=Count(
            'pk',
            filter=Q(project_status=ProjectStatus.COMPLETED),
        ),
        deadlines_soon=Count(
            'pk',
            filter=Q(
                end_date__gte=today,
                end_date__lte=next_month,
            )
            & ~Q(project_status=ProjectStatus.COMPLETED),
        ),
    )
    summary['average_progress'] = round(
        float(summary['average_progress'] or 0),
    )
    return summary
