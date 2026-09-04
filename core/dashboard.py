from datetime import timedelta

from django.db.models import F
from django.urls import reverse
from django.utils import timezone


def dashboard_callback(request, context):
    """Tambahkan KPI operasional ringkas ke halaman awal Unfold."""
    from core.models import ApprovalRequest, ApprovalStatus, DataExportJob
    from inventory.models import (
        MaterialOnProject,
        PurchaseRequest,
        PurchaseRequestStatus,
        ToolMaintenance,
        ToolMaintenanceStatus,
    )
    from project.models import (
        Document,
        DocumentStatus,
        Drawing,
        Project,
        ProjectStatus,
        Schedule,
        ScheduleStatusType,
    )
    from team.models import Attendance, AttendanceStatus, Notifications

    today = timezone.localdate()
    soon = today + timedelta(days=7)
    pending_approvals = ApprovalRequest.objects.filter(
        status=ApprovalStatus.PENDING
    )
    low_stock = MaterialOnProject.objects.filter(
        material__minimum_stock__gt=0,
        stock__lt=F('material__minimum_stock') + F('quantity_used'),
    )
    due_documents = (
        Document.objects.filter(
            due_date__range=(today, soon)
        ).exclude(status=DocumentStatus.APPROVED).count()
        + Drawing.objects.filter(
            due_date__range=(today, soon)
        ).exclude(status=DocumentStatus.APPROVED).count()
    )

    context.update(
        {
            'kpis': [
                {
                    'title': 'Proyek aktif',
                    'value': Project.objects.exclude(
                        project_status__in=[
                            ProjectStatus.COMPLETED,
                            ProjectStatus.CANCELLED,
                        ]
                    ).count(),
                    'icon': 'apartment',
                    'link': reverse('admin:project_project_changelist'),
                },
                {
                    'title': 'Approval menunggu',
                    'value': pending_approvals.count(),
                    'icon': 'approval',
                    'link': reverse(
                        'admin:core_approvalrequest_changelist'
                    ),
                },
                {
                    'title': 'Deadline 7 hari',
                    'value': due_documents,
                    'icon': 'event_upcoming',
                    'link': reverse('admin:project_document_changelist'),
                },
                {
                    'title': 'Stok rendah',
                    'value': low_stock.count(),
                    'icon': 'inventory',
                    'link': reverse(
                        'admin:inventory_materialonproject_changelist'
                    ),
                },
                {
                    'title': 'Jadwal overdue',
                    'value': Schedule.objects.filter(
                        status=ScheduleStatusType.OVERDUE
                    ).count(),
                    'icon': 'warning',
                    'link': reverse('admin:project_schedule_changelist'),
                },
                {
                    'title': 'Tidak hadir hari ini',
                    'value': Attendance.objects.filter(
                        date=today,
                        status=AttendanceStatus.ABSENT,
                    ).count(),
                    'icon': 'person_off',
                    'link': reverse('admin:team_attendance_changelist'),
                },
            ],
            'operations': [
                {
                    'label': 'Purchase request terbuka',
                    'value': PurchaseRequest.objects.filter(
                        status__in=[
                            PurchaseRequestStatus.PENDING,
                            PurchaseRequestStatus.APPROVED,
                            PurchaseRequestStatus.ORDERED,
                        ]
                    ).count(),
                    'link': reverse(
                        'admin:inventory_purchaserequest_changelist'
                    ),
                },
                {
                    'label': 'Maintenance alat aktif',
                    'value': ToolMaintenance.objects.filter(
                        status__in=[
                            ToolMaintenanceStatus.SCHEDULED,
                            ToolMaintenanceStatus.IN_PROGRESS,
                        ]
                    ).count(),
                    'link': reverse(
                        'admin:inventory_toolmaintenance_changelist'
                    ),
                },
                {
                    'label': 'Notifikasi belum dibaca',
                    'value': Notifications.objects.filter(
                        is_read=False
                    ).count(),
                    'link': reverse(
                        'admin:team_notifications_changelist'
                    ),
                },
                {
                    'label': 'Export gagal',
                    'value': DataExportJob.objects.filter(
                        status='failed'
                    ).count(),
                    'link': reverse(
                        'admin:core_dataexportjob_changelist'
                    ),
                },
            ],
            'recent_approvals': pending_approvals.select_related(
                'requested_by', 'content_type'
            )[:8],
        }
    )
    return context
