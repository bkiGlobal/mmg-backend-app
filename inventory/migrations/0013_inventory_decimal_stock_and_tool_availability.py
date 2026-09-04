from decimal import Decimal

from django.db import migrations, models
from django.db.models import Sum
from django.utils import timezone


def normalize_inventory_data(apps, schema_editor):
    MaterialOnProject = apps.get_model(
        'inventory', 'MaterialOnProject'
    )
    Tool = apps.get_model('inventory', 'Tool')
    ToolOnProject = apps.get_model('inventory', 'ToolOnProject')
    database = schema_editor.connection.alias

    duplicate_groups = (
        MaterialOnProject.objects.using(database)
        .filter(is_deleted=False, material__isnull=False)
        .values('project_id', 'material_id')
        .annotate(row_count=models.Count('pk'))
        .filter(row_count__gt=1)
    )
    for group in duplicate_groups.iterator(chunk_size=200):
        rows = list(
            MaterialOnProject.objects.using(database)
            .filter(
                is_deleted=False,
                project_id=group['project_id'],
                material_id=group['material_id'],
            )
            .order_by('created_at', 'pk')
        )
        primary = rows[0]
        primary.stock = sum(
            (Decimal(str(row.stock or 0)) for row in rows),
            Decimal('0'),
        )
        primary.quantity_used = sum(
            (Decimal(str(row.quantity_used or 0)) for row in rows),
            Decimal('0'),
        )
        if primary.quantity_used > primary.stock:
            primary.stock = primary.quantity_used
        primary.save(update_fields=['stock', 'quantity_used'])

        duplicate_ids = [row.pk for row in rows[1:]]
        MaterialOnProject.objects.using(database).filter(
            pk__in=duplicate_ids
        ).update(
            is_deleted=True,
            deleted_at=timezone.now(),
        )

    for row in MaterialOnProject.objects.using(database).all().iterator(
        chunk_size=500
    ):
        stock = max(Decimal(str(row.stock or 0)), Decimal('0'))
        quantity_used = max(
            Decimal(str(row.quantity_used or 0)),
            Decimal('0'),
        )
        if quantity_used > stock:
            stock = quantity_used
        MaterialOnProject.objects.using(database).filter(
            pk=row.pk
        ).update(stock=stock, quantity_used=quantity_used)

    ToolOnProject.objects.using(database).filter(amount__lte=0).update(
        amount=1
    )
    for tool in Tool.objects.using(database).all().iterator(chunk_size=500):
        allocated = (
            ToolOnProject.objects.using(database)
            .filter(
                tool_id=tool.pk,
                is_deleted=False,
                returned_date__isnull=True,
            )
            .aggregate(value=Sum('amount'))['value']
            or 0
        )
        amount = max(tool.amount or 0, allocated)
        Tool.objects.using(database).filter(pk=tool.pk).update(
            amount=amount,
            available=amount - allocated,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_alter_toolonproject_returned_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='materialonproject',
            name='stock',
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='materialonproject',
            name='quantity_used',
            field=models.DecimalField(
                decimal_places=4,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
        migrations.RunPython(
            normalize_inventory_data,
            migrations.RunPython.noop,
        ),
    ]
