# Generated by Django 5.2.1 on 2025-06-24 08:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0015_alter_attendance_check_out_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendance',
            name='check_in',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
