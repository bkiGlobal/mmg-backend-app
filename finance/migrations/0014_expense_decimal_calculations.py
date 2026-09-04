from decimal import Decimal, ROUND_HALF_UP

import djmoney.models.fields
from django.db import migrations, models
from django.db.models import Sum


MONEY_QUANT = Decimal('0.01')


def recalculate_existing_expenses(apps, schema_editor):
    ExpenseOnProject = apps.get_model('finance', 'ExpenseOnProject')
    ExpenseDetail = apps.get_model('finance', 'ExpenseDetail')
    ExpenseForMaterial = apps.get_model('finance', 'ExpenseForMaterial')
    database = schema_editor.connection.alias

    for line_model in (ExpenseDetail, ExpenseForMaterial):
        pending_updates = []
        queryset = line_model.objects.using(database).all().iterator(
            chunk_size=500
        )
        for line in queryset:
            quantity = Decimal(str(line.quantity or 0))
            unit_price = Decimal(str(line.unit_price or 0))
            discount = Decimal(str(line.discount or 0))
            subtotal = (quantity * unit_price).quantize(
                MONEY_QUANT, rounding=ROUND_HALF_UP
            )

            if line.discount_type == 'percentage':
                discount_amount = (
                    subtotal * discount / Decimal('100')
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            elif line.discount_type == 'fixed':
                discount_amount = discount.quantize(
                    MONEY_QUANT, rounding=ROUND_HALF_UP
                )
            else:
                discount_amount = Decimal('0')

            line.subtotal = subtotal
            line.discount_amount = discount_amount
            line.total = subtotal - discount_amount
            pending_updates.append(line)

            if len(pending_updates) == 500:
                line_model.objects.using(database).bulk_update(
                    pending_updates,
                    ['subtotal', 'discount_amount', 'total'],
                    batch_size=500,
                )
                pending_updates = []

        if pending_updates:
            line_model.objects.using(database).bulk_update(
                pending_updates,
                ['subtotal', 'discount_amount', 'total'],
                batch_size=500,
            )

    for expense in ExpenseOnProject.objects.using(database).all().iterator(
        chunk_size=500
    ):
        detail_total = (
            ExpenseDetail.objects.using(database)
            .filter(expense_id=expense.pk, is_deleted=False)
            .aggregate(value=Sum('total'))['value']
            or Decimal('0')
        )
        material_total = (
            ExpenseForMaterial.objects.using(database)
            .filter(expense_id=expense.pk, is_deleted=False)
            .aggregate(value=Sum('total'))['value']
            or Decimal('0')
        )
        expense.total = detail_total + material_total
        expense.save(update_fields=['total'])


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_paymentrequest_payment_proof'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expenseonproject',
            name='total',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='quantity',
            field=models.DecimalField(decimal_places=4, max_digits=16),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=16),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='subtotal',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='discount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expensedetail',
            name='total',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='quantity',
            field=models.DecimalField(decimal_places=4, max_digits=16),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=16),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='subtotal',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='discount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='discount_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='expenseformaterial',
            name='total',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.RunPython(
            recalculate_existing_expenses,
            migrations.RunPython.noop,
        ),
    ]
