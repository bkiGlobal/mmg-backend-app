# Generated by Django 5.2.1 on 2025-06-04 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billofquantity',
            name='total',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='expenseonproject',
            name='total',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='income',
            name='total',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
