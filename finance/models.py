from django.utils import timezone
import os
import uuid
from django.db import models
from core.models import AuditModel
from django.db.models import Sum
from inventory.models import UnitType, Material
from project.models import DocumentStatus, Project
from team.models import Signature, upload_signature_proof

class ExpenseCategory(models.TextChoices):
    LABOR = "labor", "Labor"
    EQUIPMENT = "equipment", "Equipment"
    MISCELLANEOUS = "miscellaneous", "Miscellaneous"
    TRAVEL = "travel", "Travel"
    SUBCONTRACTOR = "subcontractor", "Subcontractor"
    OVERHEAD = "overhead", "Overhead"
    OTHER = "other", "Other"

class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed"

class IncomeCategory(models.TextChoices):
    DOWN_PAYMENT = "down_payment", "Down Payment"
    PROGRESS_PAYMENT = "progress_payment", "Progress Payment"
    FINAL_PAYMENT = "final_payment", "Final Payment"
    OTHER = "other", "Other"

def upload_expense_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'EXP_{timestamp_now}.jpeg'
    return os.path.join('expense_proof_photo', filename)

def upload_income_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'INC_{timestamp_now}.jpeg'
    return os.path.join('income_proof_photo', filename)

class BillOfQuantity(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    work_weight_total = models.FloatField()
    total = models.FloatField()
    start_date = models.DateField()
    end_date = models.DateField()
    notes = models.TextField()

    def __str__(self) -> str:
        return f'{self.project.project_name} BOQ {self.pk}'
    
    @property
    def project_name(self):
        return self.project.project_name
    
    def recalc_total(self):
        """
        Hitung ulang total dari semua detail di bawah objek BOQ ini.
        """
        # Kita perlu menjumlahkan `total_price` semua BillOfQuantityItemDetail
        agg = BillOfQuantityItemDetail.objects.filter(
            bill_of_quantity_item__bill_of_quantity=self
        ).aggregate(sum_total=Sum('total_price'))
        self.total = agg['sum_total'] or 0.0
        self.save(update_fields=['total'])

class BillOfQuantityItem(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill_of_quantity = models.ForeignKey(BillOfQuantity, on_delete=models.CASCADE, related_name='items')
    item_number = models.IntegerField()
    title = models.CharField(max_length=255)
    notes = models.TextField()

    def __str__(self) -> str:
        return self.title

class BillOfQuantityItemDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill_of_quantity_item = models.ForeignKey(BillOfQuantityItem, on_delete=models.CASCADE, related_name='item_details')
    item_number = models.IntegerField()
    description = models.CharField(max_length=255)
    quantity = models.FloatField()
    unit_type = models.CharField(max_length=20, choices=UnitType.choices, default=UnitType.G)
    unit_price = models.FloatField()
    total_price = models.FloatField()
    work_weight = models.FloatField()
    notes = models.TextField()

    def __str__(self) -> str:
        return f'{self.bill_of_quantity_item.title} {self.description}'
    
    def save(self, *args, **kwargs):
        self.total_price = (self.quantity or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)

        # 2) Setelah detail tersimpan, hitung ulang total di header (BOQ)
        boq = self.bill_of_quantity_item.bill_of_quantity
        boq.recalc_total()

class SignatureOnBillOfQuantity(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    boq = models.ForeignKey(BillOfQuantity, on_delete=models.CASCADE, related_name='boq_signatures')

    def __str__(self) -> str:
        return f'Signature {self.signature.user.username} on BOQ {self.boq.project.project_name}'

class ExpenseOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_expense')
    date = models.DateField()
    total = models.FloatField()
    notes = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_expense_proof)

    def __str__(self) -> str:
        return f'Expense {self.date} on {self.project.project_name}'
    
    @property
    def project_name(self):
        return self.project.project_name

class ExpenseDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_detail')
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices)
    name = models.CharField(max_length=255)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    unit = models.CharField(max_length=20, choices=UnitType.choices)
    subtotal = models.FloatField()
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.FloatField(default=0.0)
    total = models.FloatField()
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Expense Detail {self.name} on {self.expense.project.project_name}'

class ExpenseForMaterial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(ExpenseOnProject, on_delete=models.CASCADE, related_name='expense_material')
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='material_expense', null=True, blank=True)
    category = models.CharField(max_length=20, choices=ExpenseCategory.choices)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    unit = models.CharField(max_length=20, choices=UnitType.choices)
    subtotal = models.FloatField()
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.FloatField(default=0.0)
    total = models.FloatField()

    def __str__(self) -> str:
        return f'Expense Detail {self.material.name} on {self.expense.project.project_name}'
    
class Income(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_income', null=True, blank=True)
    received_from = models.CharField(max_length=255)
    total = models.FloatField()
    category = models.CharField(max_length=20, choices=IncomeCategory.choices)
    payment_date = models.DateField()
    notes = models.TextField()
    payment_proof = models.ImageField(upload_to=upload_income_proof)

    def __str__(self) -> str:
        return f'Income on {self.payment_date}'
    
    @property
    def project_name(self):
        return self.project.project_name if self.project else None

class IncomeDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    income = models.ForeignKey(Income, on_delete=models.CASCADE, related_name='income_detail')
    name = models.CharField(max_length=255)
    quantity = models.FloatField()
    unit_price = models.FloatField()
    unit = models.CharField(max_length=20, choices=UnitType.choices)
    subtotal = models.FloatField()
    discount = models.FloatField(default=0.0)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, null=True, blank=True)
    discount_amount = models.FloatField()
    total = models.FloatField()
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Income Detail {self.name} on {self.income.payment_date}'