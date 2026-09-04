from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'finance',
            '0015_inventory_tracking_and_ledger_balances',
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name='expenseonproject',
            index=models.Index(
                fields=['project', '-date', 'is_deleted'],
                name='finance_expense_admin_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='financedata',
            index=models.Index(
                fields=['project', 'date', 'is_deleted'],
                name='finance_data_project_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='financedata',
            index=models.Index(
                fields=['other', 'date', 'is_deleted'],
                name='finance_data_other_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='pettycash',
            index=models.Index(
                fields=['project', 'date', 'is_deleted'],
                name='pettycash_project_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='pettycash',
            index=models.Index(
                fields=['other', 'date', 'is_deleted'],
                name='pettycash_other_idx',
            ),
        ),
    ]
