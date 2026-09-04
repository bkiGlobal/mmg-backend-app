from datetime import timedelta

import team.models
from django.db import migrations, models
from django.db.models import F
from django.utils import timezone


def normalize_team_data(apps, schema_editor):
    TeamMember = apps.get_model('team', 'TeamMember')
    Attendance = apps.get_model('team', 'Attendance')
    LeaveRequest = apps.get_model('team', 'LeaveRequest')
    Signature = apps.get_model('team', 'Signature')
    Initial = apps.get_model('team', 'Initial')
    database = schema_editor.connection.alias

    member_groups = (
        TeamMember.objects.using(database)
        .filter(is_deleted=False)
        .values('team_id', 'user_id')
        .annotate(row_count=models.Count('pk'))
        .filter(row_count__gt=1)
    )
    for group in member_groups.iterator(chunk_size=200):
        duplicate_ids = list(
            TeamMember.objects.using(database)
            .filter(
                is_deleted=False,
                team_id=group['team_id'],
                user_id=group['user_id'],
            )
            .order_by('created_at', 'pk')
            .values_list('pk', flat=True)[1:]
        )
        TeamMember.objects.using(database).filter(
            pk__in=duplicate_ids
        ).update(is_deleted=True, deleted_at=timezone.now())

    attendance_groups = (
        Attendance.objects.using(database)
        .filter(is_deleted=False)
        .values('user_id', 'date')
        .annotate(row_count=models.Count('pk'))
        .filter(row_count__gt=1)
    )
    for group in attendance_groups.iterator(chunk_size=200):
        duplicate_ids = list(
            Attendance.objects.using(database)
            .filter(
                is_deleted=False,
                user_id=group['user_id'],
                date=group['date'],
            )
            .order_by('-updated_at', '-created_at', 'pk')
            .values_list('pk', flat=True)[1:]
        )
        Attendance.objects.using(database).filter(
            pk__in=duplicate_ids
        ).update(is_deleted=True, deleted_at=timezone.now())

    LeaveRequest.objects.using(database).filter(
        end_date__lt=F('start_date')
    ).update(end_date=F('start_date'))

    for model in (Signature, Initial):
        for item in model.objects.using(database).all().iterator(
            chunk_size=500
        ):
            model.objects.using(database).filter(pk=item.pk).update(
                expire_at=item.created_at + timedelta(days=30)
            )


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0022_teammember_notifications_soft_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='signature',
            name='expire_at',
            field=models.DateTimeField(
                default=team.models.default_signature_expiry
            ),
        ),
        migrations.AlterField(
            model_name='initial',
            name='expire_at',
            field=models.DateTimeField(
                default=team.models.default_signature_expiry
            ),
        ),
        migrations.RunPython(
            normalize_team_data,
            migrations.RunPython.noop,
        ),
    ]
