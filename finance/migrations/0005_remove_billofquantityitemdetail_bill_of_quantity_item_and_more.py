# Generated by Django 5.2.1 on 2025-06-05 07:48

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_alter_incomedetail_discount_amount'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billofquantityitemdetail',
            name='bill_of_quantity_item',
        ),
        migrations.CreateModel(
            name='BillOfQuantitySubItem',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('item_order', models.CharField(max_length=12)),
                ('title', models.CharField(max_length=255)),
                ('notes', models.TextField()),
                ('bill_of_quantity_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subitems', to='finance.billofquantityitem')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL)),
                ('deleted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_deleted_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='billofquantityitemdetail',
            name='bill_of_quantity_subitem',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='item_details', to='finance.billofquantitysubitem'),
            preserve_default=False,
        ),
    ]
