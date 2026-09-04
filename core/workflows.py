from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ApprovalEvent, ApprovalRequest, ApprovalStatus


PRIVILEGED_APPROVER_ROLES = {
    'admin',
    'ceo',
    'cto',
}


def _profile_for_user(user):
    return getattr(user, 'profile', None)


def user_can_decide(user, approval):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = _profile_for_user(user)
    role = getattr(profile, 'role', '')
    required_roles = {
        item.strip()
        for item in (approval.required_role or '').split(',')
        if item.strip()
    }
    return role in PRIVILEGED_APPROVER_ROLES or (
        bool(required_roles) and role in required_roles
    )


def _status_value(target, desired_status):
    try:
        field = target._meta.get_field('status')
    except Exception:
        return None
    for value, _label in field.choices:
        if str(value).lower() == desired_status.lower():
            return value
    return None


def _set_target_status(target, desired_status, actor):
    status_value = _status_value(target, desired_status)
    if status_value is not None:
        target.status = status_value

    profile = _profile_for_user(actor)
    if desired_status == ApprovalStatus.APPROVED:
        if hasattr(target, 'approved_by'):
            target.approved_by = profile
        if hasattr(target, 'approved_date'):
            target.approved_date = timezone.now()
        if hasattr(target, 'approved_at'):
            target.approved_at = timezone.now()

    target.save()

    # Status versi mengikuti keputusan dokumen induk. Hal ini menjaga file
    # versi terbaru tetap konsisten dan memicu sinkronisasi Document ketika
    # BOQ, payment request, atau drawing disetujui.
    for relation_name in (
        'versions',
        'drawing_versions',
        'boq_versions',
        'payment_versions',
    ):
        if not hasattr(target, relation_name):
            continue
        latest = (
            getattr(target, relation_name)
            .filter(is_deleted=False)
            .order_by('-created_at')
            .first()
        )
        if latest is None:
            continue
        version_status = _status_value(latest, desired_status)
        if version_status is not None:
            latest.status = version_status
            latest.save(update_fields=['status'])


def _notify_approvers(approval):
    from team.models import Profile
    from team.services import notify_profiles

    roles = {
        item.strip()
        for item in (approval.required_role or '').split(',')
        if item.strip()
    } | PRIVILEGED_APPROVER_ROLES
    profiles = Profile.objects.filter(
        role__in=roles,
        is_active=True,
        user__is_active=True,
    ).distinct()
    notify_profiles(
        profiles,
        title='Approval baru',
        message=f'{approval.workflow_type}: {approval.content_object}',
        category='approval',
        action_url=f'/admin/core/approvalrequest/{approval.pk}/change/',
        dedupe_key=f'approval-pending:{approval.pk}',
    )


def _notify_requester(approval):
    from team.services import notify_users

    if not approval.requested_by:
        return
    notify_users(
        [approval.requested_by],
        title=f'Approval {approval.get_status_display()}',
        message=f'{approval.workflow_type}: {approval.content_object}',
        category='approval',
        action_url=f'/admin/core/approvalrequest/{approval.pk}/change/',
        dedupe_key=f'approval-result:{approval.pk}:{approval.status}',
    )


@transaction.atomic
def submit_for_approval(
    target,
    actor,
    workflow_type,
    required_role='admin',
    comment='',
):
    if not actor or not actor.is_authenticated:
        raise PermissionDenied('Login diperlukan untuk mengajukan approval.')

    content_type = ContentType.objects.get_for_model(
        target, for_concrete_model=False
    )
    approval, created = ApprovalRequest.objects.select_for_update().get_or_create(
        content_type=content_type,
        object_id=str(target.pk),
        status=ApprovalStatus.PENDING,
        defaults={
            'workflow_type': workflow_type,
            'required_role': required_role,
            'requested_by': actor,
            'comment': comment,
        },
    )
    if not created:
        return approval

    in_review = _status_value(target, 'in_review')
    if in_review is not None:
        target.status = in_review
        target.save()

    ApprovalEvent.objects.create(
        approval=approval,
        from_status='',
        to_status=ApprovalStatus.PENDING,
        actor=actor,
        comment=comment,
    )
    transaction.on_commit(lambda: _notify_approvers(approval))
    return approval


@transaction.atomic
def decide_approval(approval, actor, approve, comment=''):
    approval = (
        ApprovalRequest.all_objects.select_for_update().get(pk=approval.pk)
    )
    if approval.status != ApprovalStatus.PENDING:
        raise ValidationError('Approval ini sudah diproses.')
    if not user_can_decide(actor, approval):
        raise PermissionDenied('Anda tidak memiliki hak approval ini.')

    target = approval.content_object
    if target is None:
        raise ValidationError('Objek approval tidak ditemukan.')

    new_status = (
        ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
    )
    _set_target_status(target, new_status, actor)

    old_status = approval.status
    approval.status = new_status
    approval.decided_by = actor
    approval.decided_at = timezone.now()
    approval.comment = comment
    approval.save(
        update_fields=[
            'status',
            'decided_by',
            'decided_at',
            'comment',
        ]
    )
    ApprovalEvent.objects.create(
        approval=approval,
        from_status=old_status,
        to_status=new_status,
        actor=actor,
        comment=comment,
    )
    transaction.on_commit(lambda: _notify_requester(approval))
    return approval
