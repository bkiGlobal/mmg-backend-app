from decimal import Decimal
from django.utils import timezone
from django.contrib import admin
import os
import uuid
from django.db import models
from core.models import AuditModel
from django.db.models import Sum
from inventory.models import UnitType, Material, MaterialOnProject
from project.models import DocumentStatus, Project, ApprovalLevel, Document, DocumentVersion
from team.models import Signature, upload_signature_proof
from core.models import *
from djmoney.models.fields import MoneyField

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
        if self.status == DocumentStatus.APPROVED:
            document_type,_ = DocumentType.objects.get_or_create(
                name="Bill of Quantity",
            )
            document,is_created = Document.objects.get_or_create(
                project=self.project,
                document_type=document_type,
                document_name=self.document_name,
                status=DocumentStatus.APPROVED,
                approval_required=self.approval_required,
                approval_level=self.approval_level,
                issue_date=self.issue_date,
                due_date=self.due_date
            )
            version = BillOfQuantityVersion.objects.filter(
                boq=self,
                status=DocumentStatus.APPROVED
            ).first()
            if is_created and version:
                    DocumentVersion.objects.create(
                        document=document,
                        document_number=version.document_number,
                        document_file=version.boq_file,
                        title=version.title,
                        status=DocumentStatus.APPROVED,
                        notes=version.notes
                    )
            elif not is_created and version:
                # Update existing document version
                DocumentVersion.objects.filter(document=document).update(
                    document_number=version.document_number,
                    document_file=version.boq_file,
                    title=version.title,
                    status=DocumentStatus.APPROVED,
                    notes=version.notes
                )
        return super().save(*args, **kwargs)
    
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
        # Jika file baru diupload
        # self.mime_type = detect_mime(self.file) 
        # if isinstance(self.file, UploadedFile):
        #     self.mime_type = self.file.content_type  # :contentReference[oaicite:3]{index=3}
        super().save(*args, **kwargs)

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
        return f'Signature {self.signature.user.username} on BOQ {self.boq.project.project_name}'

class PaymentRequest(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_payment_requests')
    payment_name = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    approval_required = models.BooleanField(default=True)
    approval_level = models.CharField(max_length=20, choices=ApprovalLevel.choices, null=True, blank=True)
    issue_date = models.DateField(verbose_name="Upload Date", default=timezone.now)
    due_date = models.DateField(verbose_name="Deadline Date", null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.payment_name}'
    
    def save(self, *args, **kwargs):
        if self.status == DocumentStatus.APPROVED:
            document_type,_ = DocumentType.objects.get_or_create(
                name="Payment Request",
            )
            document,is_created = Document.objects.get_or_create(
                project=self.project,
                document_type=document_type,
                document_name=self.payment_name,
                status=DocumentStatus.APPROVED,
                approval_required=self.approval_required,
                approval_level=self.approval_level,
                issue_date=self.issue_date,
                due_date=self.due_date
            )
            version = PaymentRequestVersion.objects.filter(
                boq=self,
                status=DocumentStatus.APPROVED
            ).first()
            if is_created and version:
                    DocumentVersion.objects.create(
                        document=document,
                        document_number=version.payment_number,
                        document_file=version.payment_file,
                        title=version.title,
                        status=DocumentStatus.APPROVED,
                        notes=version.notes
                    )
            elif not is_created and version:
                # Update existing document version
                DocumentVersion.objects.filter(document=document).update(
                    document_number=version.payment_number,
                    document_file=version.payment_file,
                    title=version.title,
                    status=DocumentStatus.APPROVED,
                    notes=version.notes
                )
        return super().save(*args, **kwargs)
    
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
        # Jika file baru diupload
        # self.mime_type = detect_mime(self.file) 
        # if isinstance(self.file, UploadedFile):
        #     self.mime_type = self.file.content_type  # :contentReference[oaicite:3]{index=3}
        super().save(*args, **kwargs)

class SignatureOnPaymentRequest(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    document = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name='payment_request_signatures')

    def __str__(self) -> str:
        return f'Signature {self.signature.user.username} on Payment Request {self.document.project.project_name}'

class ExpenseOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_expense')
    date = models.DateField()
    total = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    notes = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_expense_proof)

    def __str__(self) -> str:
        return f'Expense {self.date} on {self.project.project_name}'
    
    @property
    def project_name(self):
        return self.project.project_name
    
    def recalc_total(self):
        """
        Hitung ulang total dari semua detail di bawah objek Income ini.
        """
        # Kita perlu menjumlahkan `total_price` semua BillOfQuantityItemDetail
        agg = ExpenseDetail.objects.filter(
            expense=self
        ).aggregate(sum_total=Sum('total'))
        agg2 = ExpenseForMaterial.objects.filter(
            expense=self
        ).aggregate(sum_total=Sum('total'))
        self.total = (agg['sum_total'] or Decimal('0.0')) + (agg2['sum_total'] or Decimal('0.0'))
        self.save(update_fields=['total'])

class ExpenseDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_detail')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    subtotal = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.FloatField(default=0.0)
    total = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Expense Detail {self.name} on {self.expense.project.project_name}'
    
    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity or 0) * (self.unit_price or 0)
        if self.discount_type == DiscountType.PERCENTAGE:
            self.discount_amount = (self.subtotal * self.discount) / 100
        elif self.discount_type == DiscountType.FIXED:
            self.discount_amount = self.discount
        self.total = self.subtotal - self.discount_amount
        super().save(*args, **kwargs)

        # 2) Setelah detail tersimpan, hitung ulang total di header (Income)
        self.expense.recalc_total()

class ExpenseForMaterial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_material')
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='material_expense', null=True, blank=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    subtotal = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.FloatField(default=0.0)
    total = MoneyField(max_digits=16, decimal_places=2, default_currency='IDR')

    def __str__(self) -> str:
        return f'Expense Detail {self.material.name} on {self.expense.project.project_name}'
    
    def save(self, *args, **kwargs):
        self.subtotal = (self.quantity or 0) * (self.unit_price or 0)
        if self.discount_type == DiscountType.PERCENTAGE:
            self.discount_amount = (self.subtotal * self.discount) / 100
        elif self.discount_type == DiscountType.FIXED:
            self.discount_amount = self.discount
        self.total = self.subtotal - self.discount_amount

        matarial_project = MaterialOnProject.objects.filter(
            project=self.expense.project,
            material=self.material
        ).first()
        if self.pk is None:
            if matarial_project:
                # Update stock dan quantity_used pada MaterialOnProject
                matarial_project.stock += self.quantity
                matarial_project.save()
            else:
                # Jika MaterialOnProject belum ada, buat baru
                matarial_project = MaterialOnProject.objects.create(
                    project=self.expense.project,
                    material=self.material,
                    stock=self.quantity,
                    quantity_used=0.0,  # Atau sesuai kebutuhan
                    notes=f'Created from ExpenseForMaterial {self.expense.date}',
                    approved_by=None,  # Atau sesuai kebutuhan
                    approved_date=timezone.now()
                )
        else:
            prev = ExpenseForMaterial.objects.get(pk=self.pk)
            if prev.quantity != self.quantity and matarial_project:
                # Update stock dan quantity_used pada MaterialOnProject
                matarial_project.stock -= prev.quantity
                matarial_project.stock += self.quantity
                matarial_project.save()
        super().save(*args, **kwargs)

        # 2) Setelah detail tersimpan, hitung ulang total di header (Income)
        self.expense.recalc_total()
    
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

class FinanceData(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_finance_data', null=True, blank=True)
    other = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description = models.TextField()
    debet = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    credit = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    balance = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    photo_proof = models.ImageField(upload_to=upload_finance_proof, null=True, blank=True)

    def __str__(self) -> str:
        return f'Finance Data for {self.project.project_name}'
    
class PettyCash(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_petty_cash', null=True, blank=True)
    type = models.ForeignKey(FinanceType, on_delete=models.PROTECT)
    payment_via = models.ForeignKey(PaymentVia, on_delete=models.PROTECT)
    other = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    description = models.TextField()
    debet = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    credit = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    balance = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    photo_proof = models.ImageField(upload_to=upload_finance_proof)

    def __str__(self) -> str:
        return f'Petty Cash for {self.project.project_name}'