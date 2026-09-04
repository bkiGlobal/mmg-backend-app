from decimal import Decimal, ROUND_HALF_UP

import djmoney.models.fields
from django.db import migrations, models


MONEY_QUANT = Decimal('0.01')


def money_amount(value):
    """Return the numeric component of Decimal or django-money values."""
    if value in (None, ''):
        return Decimal('0')
    value = getattr(value, 'amount', value)
    return Decimal(str(value))


def recalculate_ledgers(apps, schema_editor):
    database = schema_editor.connection.alias

    for model_name in ('FinanceData', 'PettyCash'):
        Ledger = apps.get_model('finance', model_name)
        project_ids = (
            Ledger.objects.using(database)
            .filter(project__isnull=False)
            .values_list('project_id', flat=True)
            .distinct()
        )
        other_values = (
            Ledger.objects.using(database)
            .filter(project__isnull=True)
            .values_list('other', flat=True)
            .distinct()
        )

        for project_id in project_ids.iterator(chunk_size=500):
            _recalculate_group(
                Ledger,
                database,
                project_id=project_id,
            )
        for other in other_values.iterator(chunk_size=500):
            _recalculate_group(
                Ledger,
                database,
                other=other,
            )


def _recalculate_group(
    Ledger, database, project_id=None, other=None
):
    if project_id:
        queryset = Ledger.objects.using(database).filter(
            project_id=project_id,
            is_deleted=False,
        )
    else:
        queryset = Ledger.objects.using(database).filter(
            project__isnull=True,
            other=other,
            is_deleted=False,
        )

    running_balance = Decimal('0')
    pending_updates = []
    for row in queryset.order_by('date', 'created_at', 'pk').iterator(
        chunk_size=500
    ):
        debit = money_amount(row.debet)
        credit = money_amount(row.credit)
        running_balance = (
            running_balance + debit - credit
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        row.balance = running_balance
        pending_updates.append(row)

        if len(pending_updates) == 500:
            Ledger.objects.using(database).bulk_update(
                pending_updates,
                ['balance'],
                batch_size=500,
            )
            pending_updates = []

    if pending_updates:
        Ledger.objects.using(database).bulk_update(
            pending_updates,
            ['balance'],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0014_expense_decimal_calculations'),
        (
            'inventory',
            '0014_inventory_indexes_and_constraints',
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='expenseformaterial',
            name='inventory_applied',
            field=models.BooleanField(
                default=False,
                editable=False,
            ),
        ),
        migrations.AlterField(
            model_name='financedata',
            name='balance',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.AlterField(
            model_name='pettycash',
            name='balance',
            field=djmoney.models.fields.MoneyField(
                decimal_places=2,
                default=Decimal('0'),
                default_currency='IDR',
                editable=False,
                max_digits=16,
            ),
        ),
        migrations.RunPython(
            recalculate_ledgers,
            migrations.RunPython.noop,
        ),
    ]
