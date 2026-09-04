from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.conf import settings
from django.utils import timezone
from django.contrib import admin
from django.core.exceptions import ValidationError
import os
import uuid
from django.db import models, router, transaction
from core.models import AuditModel
from django.db.models import Sum
from inventory.models import (
    Material,
    MaterialOnProject,
    StockMovement,
    StockMovementType,
    UnitType,
)
from project.models import DocumentStatus, Project, ApprovalLevel, Document, DocumentVersion
from team.models import Signature, upload_signature_proof
from core.models import *
from djmoney.models.fields import MoneyField
from djmoney.money import Money

# class ExpenseCategory(models.TextChoices):
#     LABOR = "labor", "Labor"
#     EQUIPMENT = "equipment", "Equipment"
#     MISCELLANEOUS = "miscellaneous", "Miscellaneous"
#     TRAVEL = "travel", "Travel"
#     SUBCONTRACTOR = "subcontractor", "Subcontractor"
#     OVERHEAD = "overhead", "Overhead"
#     OTHER = "other", "Other"

class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed"


MONEY_QUANT = Decimal('0.01')


def to_decimal(value):
    if value in (None, ''):
        return Decimal('0')
    if hasattr(value, 'amount'):
        value = value.amount
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"Nilai angka tidak valid: {value}")


def calculate_expense_line(line):
    quantity = to_decimal(line.quantity)
    unit_price = to_decimal(line.unit_price)
    discount = to_decimal(line.discount)
    errors = {}

    if quantity < 0:
        errors['quantity'] = "Quantity tidak boleh negatif."
    if unit_price < 0:
        errors['unit_price'] = "Unit price tidak boleh negatif."
    if discount < 0:
        errors['discount'] = "Discount tidak boleh negatif."
    if (
        line.discount_type == DiscountType.PERCENTAGE
        and discount > Decimal('100')
    ):
        errors['discount'] = "Percentage discount maksimal 100%."
    if not line.discount_type and discount:
        errors['discount_type'] = (
            "Discount type wajib dipilih ketika discount lebih dari 0."
        )

    subtotal = (quantity * unit_price).quantize(
        MONEY_QUANT, rounding=ROUND_HALF_UP
    )
    if line.discount_type == DiscountType.PERCENTAGE:
        discount_amount = (
            subtotal * discount / Decimal('100')
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    elif line.discount_type == DiscountType.FIXED:
        discount_amount = discount.quantize(
            MONEY_QUANT, rounding=ROUND_HALF_UP
        )
    else:
        discount_amount = Decimal('0')

    if discount_amount > subtotal:
        errors['discount'] = "Discount tidak boleh melebihi subtotal."
    if errors:
        raise ValidationError(errors)

    currency = getattr(line.expense, 'total_currency', None) or 'IDR'
    line.quantity = quantity
    line.unit_price = unit_price
    line.discount = discount
    line.subtotal = Money(subtotal, currency)
    line.discount_amount = discount_amount
    line.total = Money(subtotal - discount_amount, currency)


class LedgerBalanceMixin:
    """Otomasi running balance untuk ledger FinanceData dan PettyCash."""

    @property
    def ledger_key(self):
        if self.project_id:
            return self.project_id, None
        return None, (self.other or '').strip()

    @classmethod
    def recalculate_ledger(cls, project_id=None, other=None, using=None):
        database = using or router.db_for_write(cls)
        if project_id:
            queryset = cls.objects.using(database).filter(
                project_id=project_id
            )
        else:
            queryset = cls.objects.using(database).filter(
                project__isnull=True,
                other=other,
            )

        with transaction.atomic(using=database):
            rows = list(
                queryset.select_for_update().order_by(
                    'date', 'created_at', 'pk'
                )
            )
            running_balance = Decimal('0')
            for row in rows:
                debit = to_decimal(row.debet)
                credit = to_decimal(row.credit)
                running_balance = (
                    running_balance + debit - credit
                ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
                currency = row.debet_currency or 'IDR'
                row.balance = Money(running_balance, currency)

            if rows:
                cls.all_objects.using(database).bulk_update(
                    rows,
                    ['balance', 'balance_currency'],
                    batch_size=500,
                )

        return running_balance

    def clean(self):
        super().clean()
        errors = {}
        self.other = (self.other or '').strip() or None
        debit = to_decimal(self.debet)
        credit = to_decimal(self.credit)

        if bool(self.project_id) == bool(self.other):
            errors['project'] = (
                'Pilih tepat satu ledger: project atau other.'
            )
            errors['other'] = (
                'Pilih tepat satu ledger: project atau other.'
            )
        if debit < 0:
            errors['debet'] = 'Debet tidak boleh negatif.'
        if credit < 0:
            errors['credit'] = 'Credit tidak boleh negatif.'
        if debit > 0 and credit > 0:
            errors['credit'] = (
                'Satu transaksi tidak boleh memiliki debet dan credit '
                'sekaligus.'
            )
        if debit == 0 and credit == 0:
            errors['debet'] = 'Isi salah satu nilai debet atau credit.'

        currencies = {
            self.debet_currency,
            self.credit_currency,
            self.balance_currency,
        }
        currencies.discard(None)
        if len(currencies) > 1:
            errors['balance'] = (
                'Mata uang debet, credit, dan balance harus sama.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        recalculate_balance = kwargs.pop('recalculate_balance', True)
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        affected_keys = set()

        with transaction.atomic(using=database):
            if not self._state.adding:
                previous = (
                    type(self).all_objects.using(database)
                    .select_for_update()
                    .only('project_id', 'other')
                    .get(pk=self.pk)
                )
                affected_keys.add(previous.ledger_key)

            currency = self.debet_currency or self.credit_currency or 'IDR'
            self.balance = Money(Decimal('0'), currency)
            self.full_clean()
            result = super().save(*args, **kwargs)
            affected_keys.add(self.ledger_key)

            if recalculate_balance:
                for project_id, other in affected_keys:
                    type(self).recalculate_ledger(
                        project_id=project_id,
                        other=other,
                        using=database,
                    )

                self.refresh_from_db(
                    fields=['balance', 'balance_currency']
                )
        return result

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None,
        recalculate_balance=True,
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        ledger_key = self.ledger_key
        with transaction.atomic(using=database):
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            if (
                result[0]
                and recalculate_balance
                and cascade_at is None
            ):
                type(self).recalculate_ledger(
                    project_id=ledger_key[0],
                    other=ledger_key[1],
                    using=database,
                )
        return result

    def restore(
        self, using=None, user=None, cascade_at=None,
        recalculate_balance=True,
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        ledger_key = self.ledger_key
        with transaction.atomic(using=database):
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if recalculate_balance and cascade_at is None:
                type(self).recalculate_ledger(
                    project_id=ledger_key[0],
                    other=ledger_key[1],
                    using=database,
                )
        return result

# class IncomeCategory(models.TextChoices):
#     DOWN_PAYMENT = "down_payment", "Down Payment"
#     PROGRESS_PAYMENT = "progress_payment", "Progress Payment"
#     FINAL_PAYMENT = "final_payment", "Final Payment"
#     OTHER = "other", "Other"

def upload_expense_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'EXP_{timestamp_now}.jpeg'
    return os.path.join('expense_proof_photo', filename)

def upload_income_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'INC_{timestamp_now}.jpeg'
    return os.path.join('income_proof_photo', filename)

def upload_finance_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'FNC_{timestamp_now}.jpeg'
    return os.path.join('finance_proof_photo', filename)

def upload_petty_cash_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'FNC_{timestamp_now}.jpeg'
    return os.path.join('petty_cash_proof_photo', filename)

def upload_boq(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    new_name = f"BOQ_{timestamp_now}{ext}"
    return os.path.join('boq_project', new_name)

def upload_payment_request(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    new_name = f"PYR_{timestamp_now}{ext}"
    return os.path.join('payment_request_project', new_name)

def upload_payment_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'PRP_{timestamp_now}.jpeg'
    return os.path.join('payment_proof_photo', filename)

class BillOfQuantity(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_boqs')
    document_name = models.CharField(max_length=20, default="Bill of Quantity")
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    approval_required = models.BooleanField(default=True)
    approval_level = models.CharField(max_length=20, choices=ApprovalLevel.choices, null=True, blank=True)
    issue_date = models.DateField(verbose_name="Upload Date", default=timezone.now)
    due_date = models.DateField(verbose_name="Deadline Date", null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.document_name}'

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        if self.status == DocumentStatus.APPROVED:
            from project.services import sync_approved_document

            sync_approved_document(self)
        return result

    @property
    def project_name(self):
        return self.project.project_name

class BillOfQuantityVersion(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boq = models.ForeignKey(BillOfQuantity, on_delete=models.CASCADE, related_name='boq_versions')
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    title = models.CharField(max_length=255)
    total = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    boq_file = models.FileField(upload_to=upload_boq)
    document_number = models.CharField(max_length=255)
    notes = models.TextField()

    def __str__(self) -> str:
        return f'{self.boq.document_name} {self.document_number}'

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        if (
            self.status == DocumentStatus.APPROVED
            and self.boq.status == DocumentStatus.APPROVED
        ):
            from project.services import sync_approved_document

            sync_approved_document(self.boq)
        return result

# class BillOfQuantity(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
#     work_weight_total = models.FloatField()
#     total = models.FloatField(null=True, blank=True)
#     start_date = models.DateField()
#     end_date = models.DateField()
#     notes = models.TextField()

#     def __str__(self) -> str:
#         return f'{self.project.project_name} BOQ {self.pk}'
    
#     @property
#     def project_name(self):
#         return self.project.project_name
    
#     def recalc_total(self):
#         """
#         Hitung ulang total dari semua detail di bawah objek BOQ ini.
#         """
#         # Kita perlu menjumlahkan `total_price` semua BillOfQuantityItemDetail
#         agg = BillOfQuantityItemDetail.objects.filter(
#             bill_of_quantity_subitem__bill_of_quantity_item__bill_of_quantity=self
#         ).aggregate(sum_total=Sum('total_price'))
#         self.total = agg['sum_total'] or 0.0
#         self.save(update_fields=['total'])

# class BillOfQuantityItem(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     bill_of_quantity = models.ForeignKey(BillOfQuantity, on_delete=models.CASCADE, related_name='items')
#     item_number = models.IntegerField()
#     title = models.CharField(max_length=255)
#     notes = models.TextField()

#     def __str__(self) -> str:
#         return self.title
    
# class BillOfQuantitySubItem(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     bill_of_quantity_item = models.ForeignKey(BillOfQuantityItem, on_delete=models.CASCADE, related_name='subitems')
#     item_order = models.CharField(max_length=12)
#     title = models.CharField(max_length=255)
#     notes = models.TextField()

#     def __str__(self) -> str:
#         return self.title

# class BillOfQuantityItemDetail(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     bill_of_quantity_subitem = models.ForeignKey(BillOfQuantitySubItem, on_delete=models.CASCADE, related_name='item_details')
#     item_number = models.IntegerField()
#     description = models.CharField(max_length=255)
#     quantity = models.FloatField()
#     unit_type = models.CharField(max_length=20, choices=UnitType.choices, default=UnitType.G)
#     unit_price = models.FloatField()
#     total_price = models.FloatField()
#     work_weight = models.FloatField(blank=True, null=True)
#     notes = models.TextField()

#     def __str__(self) -> str:
#         return f'{self.bill_of_quantity_subitem.title} {self.description}'
    
#     def save(self, *args, **kwargs):
#         self.total_price = (self.quantity or 0) * (self.unit_price or 0)
#         super().save(*args, **kwargs)

#         # 2) Setelah detail tersimpan, hitung ulang total di header (BOQ)
#         boq = self.bill_of_quantity_subitem.bill_of_quantity_item.bill_of_quantity
#         boq.recalc_total()

#         # 3) Sekarang parent.total sudah ter‐update, hitung work_weight untuk detail ini
#         if boq.total:
#             self.work_weight = self.total_price / boq.total
#         else:
#             self.work_weight = 0.0

#         # 4) Simpan kembali hanya field work_weight
#         super().save(update_fields=['work_weight'])

class SignatureOnBillOfQuantity(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    boq = models.ForeignKey(BillOfQuantity, on_delete=models.CASCADE, related_name='boq_signatures')

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on BOQ {self.boq.project.project_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on BOQ {self.boq.project.project_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'

class PaymentRequest(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_payment_requests')
    payment_name = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    payment_proof = models.ImageField(upload_to=upload_payment_proof, null=True, blank=True)
    approval_required = models.BooleanField(default=True)
    approval_level = models.CharField(max_length=20, choices=ApprovalLevel.choices, null=True, blank=True)
    issue_date = models.DateField(verbose_name="Upload Date", default=timezone.now)
    due_date = models.DateField(verbose_name="Deadline Date", null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.payment_name}'

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        if self.status == DocumentStatus.APPROVED:
            from project.services import sync_approved_document

            sync_approved_document(self)
        return result

    @property
    def project_name(self):
        return self.project.project_name

class PaymentRequestVersion(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='payment_versions')
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    title = models.CharField(max_length=255)
    total = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    payment_file = models.FileField(upload_to=upload_payment_request)
    payment_number = models.CharField(max_length=255)
    notes = models.TextField()

    def __str__(self) -> str:
        return f'{self.payment_request.payment_name} {self.payment_number}'

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        if (
            self.status == DocumentStatus.APPROVED
            and self.payment_request.status == DocumentStatus.APPROVED
        ):
            from project.services import sync_approved_document

            sync_approved_document(self.payment_request)
        return result

class SignatureOnPaymentRequest(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    document = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='payment_request_signatures')

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on Payment Request {self.document.project.project_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on Payment Request {self.document.project.project_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'

class ExpenseOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_expense')
    date = models.DateField()
    total = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    notes = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_expense_proof)

    class Meta:
        indexes = [
            models.Index(
                fields=('project', '-date', 'is_deleted'),
                name='finance_expense_admin_idx',
            ),
        ]

    def __str__(self) -> str:
        return f'Expense {self.date} on {self.project.project_name}'
    
    @property
    def project_name(self):
        return self.project.project_name
    
    def recalculate_total(self, using=None):
        """Hitung total sekali, hanya dari child aktif, dengan lock parent."""
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )

        with transaction.atomic(using=database):
            locked_expense = ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.pk)
            currency = locked_expense.total_currency or 'IDR'

            detail_queryset = ExpenseDetail.objects.using(database).filter(
                expense_id=self.pk
            )
            material_queryset = ExpenseForMaterial.objects.using(
                database
            ).filter(expense_id=self.pk)

            if (
                detail_queryset.exclude(total_currency=currency).exists()
                or material_queryset.exclude(total_currency=currency).exists()
            ):
                raise ValidationError(
                    "Semua detail expense harus memakai mata uang yang sama."
                )

            detail_total = detail_queryset.aggregate(
                value=Sum('total')
            )['value'] or Decimal('0')
            material_total = material_queryset.aggregate(
                value=Sum('total')
            )['value'] or Decimal('0')
            total_amount = detail_total + material_total

            locked_expense.total = Money(total_amount, currency)
            locked_expense.save(
                using=database,
                update_fields=['total'],
            )

            self.total = locked_expense.total
            self.total_currency = locked_expense.total_currency

        return self.total

    # Alias untuk kompatibilitas pemanggil lama.
    recalc_total = recalculate_total

    def _adjust_material_stock(self, multiplier, using):
        material_totals = (
            ExpenseForMaterial.all_objects.using(using)
            .filter(
                expense_id=self.pk,
                is_deleted=False,
                inventory_applied=True,
                material__isnull=False,
            )
            .values('material_id')
            .annotate(quantity_total=Sum('quantity'))
        )
        for item in material_totals:
            ExpenseForMaterial.adjust_inventory_stock(
                project_id=self.project_id,
                material_id=item['material_id'],
                delta=to_decimal(item['quantity_total']) * multiplier,
                using=using,
                reference_id=self.pk,
            )

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            current = (
                ExpenseOnProject.all_objects.using(database)
                .select_for_update()
                .get(pk=self.pk)
            )
            if cascade_at is None and not current.is_deleted:
                self._adjust_material_stock(
                    multiplier=Decimal('-1'),
                    using=database,
                )
            return super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )

    def restore(self, using=None, user=None, cascade_at=None):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            current = (
                ExpenseOnProject.all_objects.using(database)
                .select_for_update()
                .get(pk=self.pk)
            )
            should_adjust_stock = (
                cascade_at is None and current.is_deleted
            )
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if should_adjust_stock:
                self._adjust_material_stock(
                    multiplier=Decimal('1'),
                    using=database,
                )
            return result

class ExpenseDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_detail')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit_price = models.DecimalField(max_digits=16, decimal_places=2)
    subtotal = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    discount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal('0')
    )
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal('0'),
        editable=False
    )
    total = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Expense Detail {self.name} on {self.expense.project.project_name}'
    
    def clean(self):
        super().clean()
        calculate_expense_line(self)

    def save(self, *args, **kwargs):
        recalculate = kwargs.pop('recalculate', True)
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database

        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            calculate_expense_line(self)
            super().save(*args, **kwargs)
            if recalculate and not self.expense.is_deleted:
                self.expense.recalculate_total(using=database)

    def delete(
        self, using=None, keep_parents=False, user=None, recalculate=True,
        cascade_at=None,
    ):
        expense = self.expense
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            if recalculate and not expense.is_deleted:
                expense.recalculate_total(using=database)
        return result

    def restore(
        self, using=None, user=None, recalculate=True, cascade_at=None
    ):
        expense = self.expense
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if (
                recalculate
                and cascade_at is None
                and not expense.is_deleted
            ):
                expense.recalculate_total(using=database)
        return result

class ExpenseForMaterial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_material')
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='material_expense', null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit_price = models.DecimalField(max_digits=16, decimal_places=2)
    subtotal = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    discount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal('0')
    )
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal('0'),
        editable=False
    )
    total = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    inventory_applied = models.BooleanField(
        default=False,
        editable=False,
    )

    def __str__(self) -> str:
        material_name = self.material.name if self.material else 'Unspecified'
        return (
            f'Expense Detail {material_name} '
            f'on {self.expense.project.project_name}'
        )
    
    def clean(self):
        super().clean()
        calculate_expense_line(self)

    @classmethod
    def adjust_inventory_stock(
        cls, project_id, material_id, delta, using, reference_id=''
    ):
        delta = to_decimal(delta)
        if not material_id or delta == 0:
            return None

        # Lock project menserialisasi get-or-create row stok per proyek.
        Project.all_objects.using(using).select_for_update().get(pk=project_id)
        material_project = (
            MaterialOnProject.objects.using(using)
            .select_for_update()
            .filter(project_id=project_id, material_id=material_id)
            .first()
        )

        if material_project is None:
            if delta < 0:
                raise ValidationError(
                    'Stock material proyek tidak ditemukan untuk dikurangi.'
                )
            material_project = MaterialOnProject(
                project_id=project_id,
                material_id=material_id,
                stock=delta,
                quantity_used=Decimal('0'),
                notes='Dibuat otomatis dari expense material.',
                approved_date=timezone.now(),
            )
        else:
            material_project.stock += delta

        material_project.save(using=using)
        StockMovement.objects.using(using).create(
            project_id=project_id,
            material_id=material_id,
            movement_type=StockMovementType.EXPENSE,
            quantity=delta,
            balance_after=material_project.stock,
            reference_type='expense',
            reference_id=str(reference_id or ''),
            notes='Sinkronisasi otomatis dari expense material.',
        )
        return material_project

    def save(self, *args, **kwargs):
        recalculate = kwargs.pop('recalculate', True)
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            calculate_expense_line(self)
            stock_deltas = {}
            if not self._state.adding:
                previous = (
                    ExpenseForMaterial.all_objects.using(database)
                    .select_for_update()
                    .select_related('expense')
                    .get(pk=self.pk)
                )
                if (
                    not previous.is_deleted
                    and previous.inventory_applied
                    and previous.material_id
                ):
                    old_key = (
                        previous.expense.project_id,
                        previous.material_id,
                    )
                    stock_deltas[old_key] = -to_decimal(previous.quantity)

            if not self.is_deleted and self.material_id:
                new_key = (self.expense.project_id, self.material_id)
                stock_deltas[new_key] = (
                    stock_deltas.get(new_key, Decimal('0'))
                    + to_decimal(self.quantity)
                )

            super().save(*args, **kwargs)
            for (project_id, material_id), delta in stock_deltas.items():
                self.adjust_inventory_stock(
                    project_id=project_id,
                    material_id=material_id,
                    delta=delta,
                    using=database,
                    reference_id=self.pk,
                )
            inventory_applied = bool(
                not self.is_deleted and self.material_id
            )
            ExpenseForMaterial.all_objects.using(database).filter(
                pk=self.pk
            ).update(inventory_applied=inventory_applied)
            self.inventory_applied = inventory_applied
            if recalculate and not self.expense.is_deleted:
                self.expense.recalculate_total(using=database)

    def delete(
        self, using=None, keep_parents=False, user=None, recalculate=True,
        cascade_at=None,
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        expense = self.expense
        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            current = (
                ExpenseForMaterial.all_objects.using(database)
                .select_for_update()
                .select_related('expense')
                .get(pk=self.pk)
            )
            if (
                cascade_at is None
                and not current.is_deleted
                and current.inventory_applied
                and current.material_id
            ):
                self.adjust_inventory_stock(
                    project_id=current.expense.project_id,
                    material_id=current.material_id,
                    delta=-to_decimal(current.quantity),
                    using=database,
                    reference_id=self.pk,
                )
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            if recalculate and not expense.is_deleted:
                expense.recalculate_total(using=database)
        return result

    def restore(
        self, using=None, user=None, recalculate=True, cascade_at=None
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        expense = self.expense
        with transaction.atomic(using=database):
            ExpenseOnProject.all_objects.using(
                database
            ).select_for_update().get(pk=self.expense_id)
            current = (
                ExpenseForMaterial.all_objects.using(database)
                .select_for_update()
                .select_related('expense')
                .get(pk=self.pk)
            )
            should_adjust_stock = (
                cascade_at is None
                and current.is_deleted
                and current.inventory_applied
                and current.material_id
            )
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if should_adjust_stock:
                self.adjust_inventory_stock(
                    project_id=current.expense.project_id,
                    material_id=current.material_id,
                    delta=to_decimal(current.quantity),
                    using=database,
                    reference_id=self.pk,
                )
            if recalculate and cascade_at is None and not expense.is_deleted:
                expense.recalculate_total(using=database)
        return result

# class Income(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_income', null=True, blank=True)
#     category = models.ForeignKey(IncomeCategory, on_delete=models.PROTECT)
#     received_from = models.CharField(max_length=255)
#     total = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
#     payment_date = models.DateField()
#     notes = models.TextField()
#     payment_proof = models.ImageField(upload_to=upload_income_proof)

#     def __str__(self) -> str:
#         return f'Income on {self.payment_date}'
    
#     @property
#     def project_name(self):
#         return self.project.project_name if self.project else None
    
#     def recalc_total(self):
#         """
#         Hitung ulang total dari semua detail di bawah objek Income ini.
#         """
#         # Kita perlu menjumlahkan `total_price` semua BillOfQuantityItemDetail
#         agg = IncomeDetail.objects.filter(
#             income=self
#         ).aggregate(sum_total=Sum('total'))
#         self.total = agg['sum_total'] or Decimal('0.0')
#         self.save(update_fields=['total'])

# class IncomeDetail(AuditModel):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     income = models.ForeignKey(Income, on_delete=models.CASCADE, related_name='income_detail')
#     unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
#     name = models.CharField(max_length=255)
#     quantity = models.FloatField()
#     unit_price = models.FloatField()
#     subtotal = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')
#     discount = models.FloatField(default=0.0)
#     discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
#     discount_amount = models.FloatField(default=0.0)
#     total = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')
#     notes = models.TextField()

#     def __str__(self) -> str:
#         return f'Income Detail {self.name} on {self.income.payment_date}'
    
#     def save(self, *args, **kwargs):
#         self.subtotal = (self.quantity or 0) * (self.unit_price or 0)
#         if self.discount_type == DiscountType.PERCENTAGE:
#             self.discount_amount = (self.subtotal * self.discount) / 100
#         elif self.discount_type == DiscountType.FIXED:
#             self.discount_amount = self.discount
#         self.total = self.subtotal - self.discount_amount
#         super().save(*args, **kwargs)

#         # 2) Setelah detail tersimpan, hitung ulang total di header (Income)
#         self.income.recalc_total()

class FinanceData(LedgerBalanceMixin, AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_finance_data', null=True, blank=True)
    other = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description = models.TextField()
    debet = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    credit = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    balance = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    photo_proof = models.ImageField(upload_to=upload_finance_proof, null=True, blank=True)
    is_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciled_finance_data',
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'date', 'is_deleted'),
                name='finance_data_project_idx',
            ),
            models.Index(
                fields=('other', 'date', 'is_deleted'),
                name='finance_data_other_idx',
            ),
        ]

    def __str__(self) -> str:
        if self.project:
            return f'Finance Data for {self.project.project_name}'
        elif self.other:
            return f'Finance Data for {self.other}'
        else:
            return f'Finance Data on {self.date}'
    
class PettyCash(LedgerBalanceMixin, AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_petty_cash', null=True, blank=True)
    type = models.ForeignKey(FinanceType, on_delete=models.PROTECT)
    payment_via = models.ForeignKey(PaymentVia, on_delete=models.PROTECT)
    other = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description = models.TextField()
    debet = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    credit = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    balance = MoneyField(
        max_digits=16, decimal_places=2, default=0,
        default_currency='IDR', editable=False
    )
    photo_proof = models.ImageField(upload_to=upload_finance_proof)
    is_reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciled_petty_cash',
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'date', 'is_deleted'),
                name='pettycash_project_idx',
            ),
            models.Index(
                fields=('other', 'date', 'is_deleted'),
                name='pettycash_other_idx',
            ),
        ]

    def __str__(self) -> str:
        if self.project:
            return f'Petty Cash for {self.project.project_name}'
        elif self.other:
            return f'Petty Cash for {self.other}'
        else:
            return f'Petty Cash on {self.date}'
