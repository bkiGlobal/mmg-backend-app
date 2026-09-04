from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0014_project_validation_constraints'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='project',
            index=models.Index(
                fields=['project_status', '-start_date', 'is_deleted'],
                name='project_admin_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='document',
            index=models.Index(
                fields=['project', 'status', '-issue_date', 'is_deleted'],
                name='project_document_admin_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='drawing',
            index=models.Index(
                fields=['project', 'status', '-issue_date', 'is_deleted'],
                name='project_drawing_admin_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.CheckConstraint(
                condition=Q(progress__gte=0, progress__lte=100),
                name='project_progress_between_0_100',
            ),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.CheckConstraint(
                condition=(
                    Q(end_date__isnull=True)
                    | Q(end_date__gte=F('start_date'))
                ),
                name='project_end_on_or_after_start',
            ),
        ),
        migrations.AddConstraint(
            model_name='document',
            constraint=models.CheckConstraint(
                condition=Q(due_date__gte=F('issue_date')),
                name='project_document_due_on_or_after_issue',
            ),
        ),
        migrations.AddConstraint(
            model_name='drawing',
            constraint=models.CheckConstraint(
                condition=Q(due_date__gte=F('issue_date')),
                name='project_drawing_due_on_or_after_issue',
            ),
        ),
        migrations.AddConstraint(
            model_name='errorlog',
            constraint=models.CheckConstraint(
                condition=(
                    Q(periode_end__isnull=True)
                    | Q(periode_end__gte=F('periode_start'))
                ),
                name='project_error_end_on_or_after_start',
            ),
        ),
        migrations.AddConstraint(
            model_name='schedule',
            constraint=models.CheckConstraint(
                condition=Q(duration__gt=0),
                name='project_schedule_duration_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='schedule',
            constraint=models.CheckConstraint(
                condition=Q(end_date__gte=F('start_date')),
                name='project_schedule_end_on_or_after_start',
            ),
        ),
        migrations.AddConstraint(
            model_name='progressreport',
            constraint=models.CheckConstraint(
                condition=Q(progress_number__gt=0),
                name='project_report_number_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='progressreport',
            constraint=models.CheckConstraint(
                condition=Q(
                    progress_percentage__gte=0,
                    progress_percentage__lte=100,
                ),
                name='project_report_progress_between_0_100',
            ),
        ),
    ]
