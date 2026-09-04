from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        (
            'inventory',
            '0013_inventory_decimal_stock_and_tool_availability',
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name='tool',
            name='amount',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='tool',
            name='available',
            field=models.PositiveIntegerField(
                default=0,
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name='toolonproject',
            name='amount',
            field=models.PositiveIntegerField(),
        ),
        migrations.AddIndex(
            model_name='materialonproject',
            index=models.Index(
                fields=['project', 'is_deleted'],
                name='inventory_material_project_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='toolonproject',
            index=models.Index(
                fields=['project', 'returned_date', 'is_deleted'],
                name='inventory_tool_project_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='toolonproject',
            index=models.Index(
                fields=['tool', 'returned_date', 'is_deleted'],
                name='inventory_tool_active_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='materialonproject',
            constraint=models.UniqueConstraint(
                condition=Q(
                    is_deleted=False,
                    material__isnull=False,
                ),
                fields=('project', 'material'),
                name='inventory_unique_active_project_material',
            ),
        ),
        migrations.AddConstraint(
            model_name='materialonproject',
            constraint=models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='inventory_material_stock_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='materialonproject',
            constraint=models.CheckConstraint(
                condition=Q(quantity_used__gte=0),
                name='inventory_material_used_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='materialonproject',
            constraint=models.CheckConstraint(
                condition=Q(quantity_used__lte=F('stock')),
                name='inventory_material_used_lte_stock',
            ),
        ),
        migrations.AddConstraint(
            model_name='tool',
            constraint=models.CheckConstraint(
                condition=Q(amount__gte=0),
                name='inventory_tool_amount_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='tool',
            constraint=models.CheckConstraint(
                condition=Q(available__gte=0),
                name='inventory_tool_available_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='tool',
            constraint=models.CheckConstraint(
                condition=Q(available__lte=F('amount')),
                name='inventory_tool_available_lte_amount',
            ),
        ),
        migrations.AddConstraint(
            model_name='toolonproject',
            constraint=models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='inventory_tool_assignment_amount_positive',
            ),
        ),
    ]
