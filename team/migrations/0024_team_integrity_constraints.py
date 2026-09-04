from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0023_team_integrity_constraints'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='teammember',
            constraint=models.UniqueConstraint(
                condition=Q(is_deleted=False),
                fields=('team', 'user'),
                name='team_unique_active_member',
            ),
        ),
        migrations.AddConstraint(
            model_name='attendance',
            constraint=models.UniqueConstraint(
                condition=Q(is_deleted=False),
                fields=('user', 'date'),
                name='team_unique_active_attendance_day',
            ),
        ),
        migrations.AddConstraint(
            model_name='leaverequest',
            constraint=models.CheckConstraint(
                condition=Q(end_date__gte=F('start_date')),
                name='team_leave_end_on_or_after_start',
            ),
        ),
    ]
