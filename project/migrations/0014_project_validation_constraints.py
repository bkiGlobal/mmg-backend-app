from django.db import migrations
from django.db.models import F


def normalize_project_data(apps, schema_editor):
    Project = apps.get_model('project', 'Project')
    Document = apps.get_model('project', 'Document')
    Drawing = apps.get_model('project', 'Drawing')
    ErrorLog = apps.get_model('project', 'ErrorLog')
    Schedule = apps.get_model('project', 'Schedule')
    ProgressReport = apps.get_model('project', 'ProgressReport')
    database = schema_editor.connection.alias

    Project.objects.using(database).filter(progress__lt=0).update(progress=0)
    Project.objects.using(database).filter(progress__gt=100).update(
        progress=100
    )
    Project.objects.using(database).filter(
        end_date__lt=F('start_date')
    ).update(end_date=F('start_date'))
    Document.objects.using(database).filter(
        due_date__lt=F('issue_date')
    ).update(due_date=F('issue_date'))
    Drawing.objects.using(database).filter(
        due_date__lt=F('issue_date')
    ).update(due_date=F('issue_date'))
    ErrorLog.objects.using(database).filter(
        periode_end__lt=F('periode_start')
    ).update(periode_end=F('periode_start'))
    Schedule.objects.using(database).filter(duration__lte=0).update(
        duration=1
    )
    Schedule.objects.using(database).filter(
        end_date__lt=F('start_date')
    ).update(end_date=F('start_date'))
    ProgressReport.objects.using(database).filter(
        progress_number__lte=0
    ).update(progress_number=1)
    ProgressReport.objects.using(database).filter(
        progress_percentage__lt=0
    ).update(progress_percentage=0)
    ProgressReport.objects.using(database).filter(
        progress_percentage__gt=100
    ).update(progress_percentage=100)


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0013_alter_errorlog_periode_end'),
    ]

    operations = [
        migrations.RunPython(
            normalize_project_data,
            migrations.RunPython.noop,
        ),
    ]
