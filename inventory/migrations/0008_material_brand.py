# Generated by Django 5.2.1 on 2025-06-19 03:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_brand'),
        ('inventory', '0007_alter_material_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='material',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.brand'),
        ),
    ]
