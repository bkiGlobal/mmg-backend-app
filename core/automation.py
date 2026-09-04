from datetime import timedelta

from django.utils import timezone


def _project_profiles(project):
    from team.models import Profile

    profile_ids = set()
    if project.client_id:
        profile_ids.add(project.client_id)
    if project.team_id:
        profile_ids.update(
            project.team.members.filter(
                is_active=True,
                is_deleted=False,
            ).values_list('user_id', flat=True)
        )
    return Profile.objects.filter(pk__in=profile_ids, is_active=True)


def run_daily_automations(target_date=None):
    from finance.models import BillOfQuantity, PaymentRequest
    from inventory.services import (
        create_low_stock_purchase_requests,
        schedule_due_tool_maintenance,
    )
    from project.models import (
        Document,
        DocumentStatus,
        Drawing,
        Project,
        Schedule,
        ScheduleStatusType,
    )
    from team.models import (
        Initial,
        NotificationCategory,
        Profile,
        Signature,
    )
    from team.services import generate_daily_attendance, notify_profiles

    target_date = target_date or timezone.localdate()
    reminder_limit = target_date + timedelta(days=3)
    signature_limit = target_date + timedelta(days=7)
    counts = {
        'deadline_notifications': 0,
        'signature_notifications': 0,
        'overdue_schedules': 0,
        'purchase_requests': 0,
        'maintenance_records': 0,
        'attendance_records': 0,
    }

    deadline_models = (
        (Document, 'document'),
        (Drawing, 'drawing'),
        (BillOfQuantity, 'boq'),
        (PaymentRequest, 'payment'),
    )
    for model, label in deadline_models:
        objects = model.objects.filter(
            due_date__isnull=False,
            due_date__lte=reminder_limit,
        ).exclude(status=DocumentStatus.APPROVED)
        for item in objects.select_related('project'):
            profiles = _project_profiles(item.project)
            created = notify_profiles(
                profiles,
                title='Deadline mendekat',
                message=f'{item} jatuh tempo pada {item.due_date:%d-%m-%Y}.',
                category=NotificationCategory.DEADLINE,
                dedupe_key=(
                    f'deadline:{label}:{item.pk}:{item.due_date}'
                ),
            )
            counts['deadline_notifications'] += len(created)

    for model, field_name in (
        (Signature, 'signature'),
        (Initial, 'initial'),
    ):
        for item in model.objects.filter(
            expire_at__date__lte=signature_limit
        ).select_related('user'):
            created = notify_profiles(
                [item.user],
                title='Tanda tangan segera kedaluwarsa',
                message=(
                    f'{field_name.title()} kedaluwarsa pada '
                    f'{item.expire_at:%d-%m-%Y}.'
                ),
                category=NotificationCategory.SYSTEM,
                dedupe_key=(
                    f'{field_name}-expiry:{item.pk}:{item.expire_at.date()}'
                ),
            )
            counts['signature_notifications'] += len(created)

    overdue = Schedule.objects.filter(
        end_date__lt=target_date,
    ).exclude(
        status__in=[
            ScheduleStatusType.COMPLETED,
            ScheduleStatusType.CANCELLED,
            ScheduleStatusType.CANCELLED_BY_CLIENT,
            ScheduleStatusType.ON_HOLD,
            ScheduleStatusType.OVERDUE,
        ]
    )
    counts['overdue_schedules'] = overdue.update(
        status=ScheduleStatusType.OVERDUE
    )

    for project in Project.objects.all():
        project.recalculate_progress()

    purchase_requests = create_low_stock_purchase_requests()
    counts['purchase_requests'] = len(purchase_requests)
    if purchase_requests:
        recipients = Profile.objects.filter(
            role__in=['logistic', 'pm', 'project_admin', 'cfo'],
            is_active=True,
        )
        for purchase in purchase_requests:
            notify_profiles(
                recipients,
                title='Purchase request otomatis',
                message=str(purchase),
                category=NotificationCategory.INVENTORY,
                action_url=(
                    f'/admin/inventory/purchaserequest/'
                    f'{purchase.pk}/change/'
                ),
                dedupe_key=f'purchase-request:{purchase.pk}',
            )

    maintenance = schedule_due_tool_maintenance(target_date)
    counts['maintenance_records'] = len(maintenance)
    counts['attendance_records'] = generate_daily_attendance(
        target_date - timedelta(days=1)
    )
    return counts
