from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0026_attendance_simplified_workflow'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='check_in_accuracy_meters',
            field=models.FloatField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='check_in_distance_meters',
            field=models.FloatField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='check_out_accuracy_meters',
            field=models.FloatField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='check_out_distance_meters',
            field=models.FloatField(
                blank=True,
                editable=False,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='work_mode',
            field=models.CharField(
                choices=[
                    ('office', 'Office'),
                    ('wfh', 'Work From Home'),
                ],
                default='office',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='workpolicy',
            name='allow_wfh',
            field=models.BooleanField(
                default=False,
                help_text='Izinkan staff memilih mode Work From Home.',
            ),
        ),
        migrations.AddField(
            model_name='workpolicy',
            name='wfh_geofence_radius_meters',
            field=models.PositiveIntegerField(
                default=150,
                help_text=(
                    'Radius maksimum dari alamat rumah pada profile ketika '
                    'WFH.'
                ),
            ),
        ),
    ]
