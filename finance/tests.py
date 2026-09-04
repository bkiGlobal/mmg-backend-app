from datetime import date
from decimal import Decimal
from io import BytesIO
import importlib
import tempfile
import uuid

import pandas as pd
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse
from djmoney.money import Money
from PIL import Image

from core.models import (
    DataExportJob,
    ExpenseCategory,
    ExportJobStatus,
    FinanceType,
    MaterialCategory,
    PaymentVia,
    UnitType,
)
from inventory.models import Material, MaterialOnProject
from project.models import Project

from .models import (
    DiscountType,
    ExpenseDetail,
    ExpenseForMaterial,
    ExpenseOnProject,
    FinanceData,
    PettyCash,
)
from .imports import import_expense_workbook
from .export_jobs import enqueue_export, process_export_job


class ExpenseCalculationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_name='Expense Project',
            project_code='EXP-001',
            description='Expense calculation tests',
            start_date=date(2025, 1, 1),
        )
        self.category = ExpenseCategory.objects.create(name='Test Expense')
        self.unit = UnitType.objects.create(name='Test Unit')
        self.expense = ExpenseOnProject.objects.create(
            project=self.project,
            date=date(2025, 1, 2),
            notes='Expense test',
            photo_proof='expense_proof_photo/test.jpg',
        )

    def create_detail(self, **overrides):
        values = {
            'expense': self.expense,
            'category': self.category,
            'unit': self.unit,
            'name': 'Labor',
            'quantity': Decimal('2.5000'),
            'unit_price': Decimal('1000.00'),
            'discount': Decimal('10.00'),
            'discount_type': DiscountType.PERCENTAGE,
            'notes': 'Calculated detail',
        }
        values.update(overrides)
        return ExpenseDetail.objects.create(**values)

    def test_percentage_calculation_and_parent_total(self):
        detail = self.create_detail()
        self.expense.refresh_from_db()

        self.assertEqual(detail.subtotal.amount, Decimal('2500.00'))
        self.assertEqual(detail.discount_amount, Decimal('250.00'))
        self.assertEqual(detail.total.amount, Decimal('2250.00'))
        self.assertEqual(self.expense.total.amount, Decimal('2250.00'))

    def test_batch_recalculation_can_be_deferred(self):
        detail = ExpenseDetail(
            expense=self.expense,
            category=self.category,
            unit=self.unit,
            name='Deferred detail',
            quantity=Decimal('2.0000'),
            unit_price=Decimal('500.00'),
            discount=Decimal('0'),
            notes='Deferred calculation',
        )
        detail.save(recalculate=False)

        material = ExpenseForMaterial(
            expense=self.expense,
            category=self.category,
            unit=self.unit,
            quantity=Decimal('3.0000'),
            unit_price=Decimal('100.00'),
            discount=Decimal('50.00'),
            discount_type=DiscountType.FIXED,
        )
        material.save(recalculate=False)

        self.expense.refresh_from_db()
        self.assertEqual(self.expense.total.amount, Decimal('0.00'))

        self.expense.recalculate_total()
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.total.amount, Decimal('1250.00'))

    def test_soft_delete_and_restore_recalculate_parent(self):
        detail = self.create_detail()

        detail.delete()
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.total.amount, Decimal('0.00'))
        self.assertFalse(
            ExpenseDetail.objects.filter(pk=detail.pk).exists()
        )

        deleted_detail = ExpenseDetail.all_objects.get(pk=detail.pk)
        deleted_detail.restore()
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.total.amount, Decimal('2250.00'))

    def test_percentage_discount_above_one_hundred_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.create_detail(discount=Decimal('101.00'))

    def test_material_expense_keeps_inventory_in_sync(self):
        material_category = MaterialCategory.objects.create(
            name='Test Material Category'
        )
        material = Material.objects.create(
            category=material_category,
            unit=self.unit,
            code='MAT-001',
            name='Cement',
            descriptions='Test material',
        )
        line = ExpenseForMaterial.objects.create(
            expense=self.expense,
            material=material,
            category=self.category,
            unit=self.unit,
            quantity=Decimal('3.0000'),
            unit_price=Decimal('100.00'),
        )
        inventory = MaterialOnProject.objects.get(
            project=self.project,
            material=material,
        )
        self.assertEqual(inventory.stock, Decimal('3.0000'))
        self.assertTrue(line.inventory_applied)

        line.quantity = Decimal('5.0000')
        line.save()
        inventory.refresh_from_db()
        self.assertEqual(inventory.stock, Decimal('5.0000'))

        line.delete()
        inventory.refresh_from_db()
        self.assertEqual(inventory.stock, Decimal('0.0000'))

        ExpenseForMaterial.all_objects.get(pk=line.pk).restore()
        inventory.refresh_from_db()
        self.assertEqual(inventory.stock, Decimal('5.0000'))


class LedgerBalanceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_name='Ledger Project',
            project_code='LEDGER-001',
            description='Ledger tests',
            start_date=date(2025, 1, 1),
        )

    def test_running_balance_recalculates_after_delete_and_restore(self):
        first = FinanceData.objects.create(
            project=self.project,
            date=date(2025, 1, 1),
            description='Opening debit',
            debet=Decimal('100.00'),
            credit=Decimal('0'),
        )
        second = FinanceData.objects.create(
            project=self.project,
            date=date(2025, 1, 2),
            description='Expense credit',
            debet=Decimal('0'),
            credit=Decimal('40.00'),
        )
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.balance.amount, Decimal('100.00'))
        self.assertEqual(second.balance.amount, Decimal('60.00'))

        first.delete()
        second.refresh_from_db()
        self.assertEqual(second.balance.amount, Decimal('-40.00'))

        FinanceData.all_objects.get(pk=first.pk).restore()
        second.refresh_from_db()
        self.assertEqual(second.balance.amount, Decimal('60.00'))

    def test_ledger_migration_accepts_money_objects(self):
        migration = importlib.import_module(
            'finance.migrations.'
            '0015_inventory_tracking_and_ledger_balances'
        )

        self.assertEqual(
            migration.money_amount(Money('1250.50', 'IDR')),
            Decimal('1250.50'),
        )
        self.assertEqual(
            migration.money_amount(Decimal('25.50')),
            Decimal('25.50'),
        )
        self.assertEqual(migration.money_amount(None), Decimal('0'))


class LedgerSpreadsheetAdminTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.superuser = User.objects.create_superuser(
            username='ledger-spreadsheet-admin',
            email='ledger-sheet@example.com',
            password='test-password',
        )
        self.project = Project.objects.create(
            project_name='Spreadsheet Project',
            project_code='SHEET-001',
            description='Spreadsheet entry tests',
            start_date=date(2026, 7, 1),
        )
        self.finance_type, _ = FinanceType.objects.get_or_create(
            name='Operational'
        )
        self.payment_via, _ = PaymentVia.objects.get_or_create(name='Cash')
        self.client.force_login(self.superuser)

    @staticmethod
    def image_upload(name):
        content = BytesIO()
        Image.new('RGB', (8, 8), color='#d4af37').save(
            content,
            format='JPEG',
        )
        return SimpleUploadedFile(
            name,
            content.getvalue(),
            content_type='image/jpeg',
        )

    @staticmethod
    def management_data(total):
        return {
            'rows-TOTAL_FORMS': str(total),
            'rows-INITIAL_FORMS': '0',
            'rows-MIN_NUM_FORMS': '0',
            'rows-MAX_NUM_FORMS': '50',
        }

    def test_ledger_changelists_offer_spreadsheet_entry(self):
        # Label tombol diambil dari konfigurasi admin supaya tes tetap sahih
        # ketika teksnya dipendekkan demi layar sempit.
        from django.contrib import admin as django_admin

        from .models import FinanceData, PettyCash

        petty_label = django_admin.site._registry[
            PettyCash
        ].spreadsheet_button_label
        finance_label = django_admin.site._registry[
            FinanceData
        ].spreadsheet_button_label

        petty_list = self.client.get(
            reverse('admin:finance_pettycash_changelist'),
            secure=True,
        )
        finance_list = self.client.get(
            reverse('admin:finance_financedata_changelist'),
            secure=True,
        )
        petty_sheet = self.client.get(
            reverse('admin:finance_pettycash_spreadsheet'),
            secure=True,
        )

        self.assertEqual(petty_list.status_code, 200)
        self.assertContains(petty_list, petty_label)
        self.assertContains(petty_list, 'FINANCIAL SNAPSHOT')
        self.assertContains(petty_list, 'Ringkasan transaksi terfilter')
        self.assertContains(
            petty_list,
            reverse('admin:finance_pettycash_spreadsheet'),
        )
        self.assertNotContains(petty_list, 'class="object-tools"')
        self.assertContains(petty_list, 'class="addlink')
        self.assertEqual(finance_list.status_code, 200)
        self.assertContains(finance_list, finance_label)
        self.assertContains(
            finance_list,
            reverse('admin:finance_financedata_spreadsheet'),
        )
        self.assertContains(finance_list, 'FINANCIAL SNAPSHOT')
        self.assertEqual(petty_sheet.status_code, 200)
        self.assertContains(
            petty_sheet,
            'Petty Cash · Spreadsheet Input Mode',
        )
        self.assertContains(
            petty_sheet,
            'Terapkan Data Baris Pertama',
        )
        self.assertContains(petty_sheet, 'Simpan semua transaksi')
        self.assertContains(petty_sheet, 'id_rows-0-project')
        self.assertContains(
            petty_sheet,
            static('admin/css/ledger_spreadsheet.css'),
        )
        self.assertContains(
            petty_sheet,
            static('admin/js/ledger_spreadsheet.js'),
        )

    def test_petty_cash_spreadsheet_saves_rows_and_running_balance(self):
        payload = {
            **self.management_data(2),
            'rows-0-project': str(self.project.pk),
            'rows-0-other': '',
            'rows-0-date': '2026-07-28',
            'rows-0-type': str(self.finance_type.pk),
            'rows-0-payment_via': str(self.payment_via.pk),
            'rows-0-description': 'Petty cash opening',
            'rows-0-debet': '500000',
            'rows-0-credit': '0',
            'rows-0-photo_proof': self.image_upload('opening.jpg'),
            'rows-1-project': str(self.project.pk),
            'rows-1-other': '',
            'rows-1-date': '2026-07-29',
            'rows-1-type': str(self.finance_type.pk),
            'rows-1-payment_via': str(self.payment_via.pk),
            'rows-1-description': 'Site supplies',
            'rows-1-debet': '0',
            'rows-1-credit': '125000',
            'rows-1-photo_proof': self.image_upload('supplies.jpg'),
        }

        response = self.client.post(
            reverse('admin:finance_pettycash_spreadsheet'),
            payload,
            secure=True,
        )

        self.assertRedirects(
            response,
            reverse('admin:finance_pettycash_changelist'),
            fetch_redirect_response=False,
        )
        rows = list(PettyCash.objects.order_by('date', 'created_at'))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].balance.amount, Decimal('500000.00'))
        self.assertEqual(rows[1].balance.amount, Decimal('375000.00'))
        self.assertEqual(rows[0].created_by, self.superuser)
        self.assertTrue(rows[0].photo_proof.name)

    def test_finance_spreadsheet_supports_other_ledger_without_photo(self):
        payload = {
            **self.management_data(1),
            'rows-0-project': '',
            'rows-0-other': 'Head Office',
            'rows-0-date': '2026-07-29',
            'rows-0-description': 'Office float',
            'rows-0-debet': '750000',
            'rows-0-credit': '0',
        }

        response = self.client.post(
            reverse('admin:finance_financedata_spreadsheet'),
            payload,
            secure=True,
        )

        self.assertRedirects(
            response,
            reverse('admin:finance_financedata_changelist'),
            fetch_redirect_response=False,
        )
        row = FinanceData.objects.get(other='Head Office')
        self.assertEqual(row.balance.amount, Decimal('750000.00'))
        self.assertFalse(bool(row.photo_proof))

    def test_spreadsheet_rejects_project_and_other_in_same_row(self):
        payload = {
            **self.management_data(1),
            'rows-0-project': str(self.project.pk),
            'rows-0-other': 'Duplicate ledger',
            'rows-0-date': '2026-07-29',
            'rows-0-description': 'Invalid row',
            'rows-0-debet': '1000',
            'rows-0-credit': '0',
        }

        response = self.client.post(
            reverse('admin:finance_financedata_spreadsheet'),
            payload,
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Pilih tepat satu ledger: project atau ledger lain.',
        )
        self.assertFalse(
            FinanceData.objects.filter(description='Invalid row').exists()
        )


class ExpenseWorkbookImportTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_name='Import Project',
            project_code='IMPORT-001',
            description='Atomic import tests',
            start_date=date(2026, 1, 1),
        )
        self.category = ExpenseCategory.objects.create(
            name='Import Expense Category'
        )
        self.unit = UnitType.objects.create(name='Import Unit')

    def workbook_frames(self, invalid_category=False):
        expense_id = uuid.uuid4()
        expense = pd.DataFrame(
            [
                {
                    'id': str(expense_id),
                    'project': str(self.project.pk),
                    'date': date(2026, 1, 2),
                    'notes': 'Imported expense',
                    'photo_proof': 'expense_proof_photo/import.jpg',
                }
            ]
        )
        detail = pd.DataFrame(
            [
                {
                    'id': str(uuid.uuid4()),
                    'expense': str(expense_id),
                    'category': (
                        str(uuid.uuid4())
                        if invalid_category
                        else self.category.pk
                    ),
                    'unit': self.unit.pk,
                    'name': 'Imported labor',
                    'quantity': Decimal('2'),
                    'unit_price': Decimal('500'),
                    'discount': Decimal('10'),
                    'discount_type': DiscountType.PERCENTAGE,
                    'notes': 'Imported detail',
                }
            ]
        )
        return expense, detail, pd.DataFrame()

    def test_import_recalculates_server_managed_totals(self):
        counts = import_expense_workbook(*self.workbook_frames())

        imported = ExpenseOnProject.objects.get(
            project=self.project,
            notes='Imported expense',
        )
        self.assertEqual(counts['expense_created'], 1)
        self.assertEqual(counts['detail_created'], 1)
        self.assertEqual(imported.total.amount, Decimal('900.00'))

    def test_invalid_child_rolls_back_entire_workbook(self):
        with self.assertRaises(ValidationError):
            import_expense_workbook(
                *self.workbook_frames(invalid_category=True)
            )

        self.assertFalse(
            ExpenseOnProject.objects.filter(
                project=self.project,
                notes='Imported expense',
            ).exists()
        )


class AsyncExportTests(TestCase):
    def test_queued_export_creates_downloadable_workbook(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                job = DataExportJob.objects.create(job_type='expense')
                process_export_job(job)
                job.refresh_from_db()

                self.assertEqual(
                    job.status, ExportJobStatus.COMPLETED
                )
                self.assertTrue(job.result_file.name.endswith('.xlsx'))
                self.assertTrue(job.result_file.storage.exists(
                    job.result_file.name
                ))

    def test_enqueue_runs_inline_when_no_scheduler_available(self):
        """Server lokal tidak menjalankan cron, jadi job harus langsung
        selesai supaya tidak menggantung di status queued."""
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(
                MEDIA_ROOT=media_root,
                EXPORT_JOBS_RUN_INLINE=True,
            ):
                job = enqueue_export('expense')

                self.assertEqual(job.status, ExportJobStatus.COMPLETED)
                self.assertTrue(job.result_file.name.endswith('.xlsx'))

    def test_enqueue_stays_queued_when_scheduler_handles_it(self):
        with override_settings(EXPORT_JOBS_RUN_INLINE=False):
            job = enqueue_export('expense')

            self.assertEqual(job.status, ExportJobStatus.QUEUED)
            self.assertIsNone(job.started_at)
