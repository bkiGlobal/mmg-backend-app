import os
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, router, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from core.models import *
from project.models import Project
from team.models import Profile
from djmoney.models.fields import MoneyField

# class UnitType(models.TextChoices):
#     KG = "kg", "Kilogram"
#     G = "g", "Gram"
#     TON = "ton", "Ton"
#     LB = "lb", "Pound"
#     M3 = "m3", "Cubic Meter"
#     L = "l", "Litre"
#     ML = "ml", "Millilitre"
#     GAL = "gal", "Gallon"
#     FT3 = "ft3", "Cubic Feet"
#     M = "m", "Meter"
#     CM = "cm", "Centimeter"
#     MM = "mm", "Millimeter"
#     INCH = "in", "Inch"
#     FT = "ft", "Foot"
#     M2 = "m2", "Square Meter"
#     FT2 = "ft2", "Square Feet"
#     UNIT = "unit", "Unit"
#     PCS = "pcs", "Piece"
#     SET = "set", "Set"
#     BOX = "box", "Box"
#     ROLL = "roll", "Roll"
#     PACK = "pack", "Pack"
#     SHEET = "sheet", "Sheet"
#     BAG = "bag", "Bag"
#     SACK = "sack", "Sack"
#     DRUM = "drum", "Drum"
#     BUNDLE = "bundle", "Bundle"
#     PALLET = "pallet", "Pallet"
#     TUBE = "tube", "Tube"
#     BOTTLE = "bottle", "Bottle"
#     CAN = "can", "Can"
#     CARTON = "carton", "Carton"
#     TRAY = "tray", "Tray"
#     ROLLER = "roller", "Roller"
#     MONTH = "month", "Month"
#     LUMP_SUM = "ls", "Lump Sum"

# class MaterialCategory(models.TextChoices):
#     STRUCTURAL = "structural", "Structural"
#     FINISHING = "finishing", "Finishing"
#     ELECTRICAL = "electrical", "Electrical"
#     PLUMBING = "plumbing", "Plumbing"
#     HARDWARE = "hardware", "Hardware"
#     CHEMICAL = "chemical", "Chemical"
#     INTERIOR = "interior", "Interior"
#     EXTERIOR = "exterior", "Exterior"
#     OTHER = "other", "Other"

# class ToolCategory(models.TextChoices):
#     HAND_TOOL = "hand_tool", "Hand Tool"
#     POWER_TOOL = "power_tool", "Power Tool"
#     MEASURING = "measuring", "Measuring"
#     SAFETY = "safety", "Safety"
#     HEAVY_EQUIPMENT = "heavy_equipment", "Heavy Equipment"
#     CUTTING = "cutting", "Cutting"
#     LIFTING = "lifting", "Lifting"
#     DEMOLITION = "demolition", "Demolition"
#     OTHER = "other", "Other"

def upload_tools(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'TLS_{timestamp_now}.jpeg'
    return os.path.join('tool', filename)

def upload_materials(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'MTR_{timestamp_now}.jpeg'
    return os.path.join('material', filename)

def upload_materials_project(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'MDT_{timestamp_now}.jpeg'
    return os.path.join('material_project', filename)

class Material(AuditModel):
    soft_delete_related = ('material_project',)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    unit = models.ForeignKey(UnitType, on_delete=models.PROTECT)
    photo = models.ImageField(upload_to=upload_materials, null=True, blank=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=128)
    standart_price = MoneyField(max_digits=16, decimal_places=2, default=0, default_currency='IDR')
    minimum_stock = models.DecimalField(
        max_digits=16, decimal_places=4, default=Decimal('0')
    )
    descriptions = models.TextField()

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.minimum_stock < 0:
            raise ValidationError(
                {'minimum_stock': 'Minimum stock tidak boleh negatif.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
class MaterialOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_material')
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, related_name='material_project', null=True, blank=True)
    photo = models.ImageField(upload_to=upload_materials_project, null=True, blank=True)
    stock = models.DecimalField(
        max_digits=16, decimal_places=4, default=Decimal('0')
    )
    quantity_used = models.DecimalField(
        max_digits=16, decimal_places=4, default=Decimal('0')
    )
    notes = models.TextField()
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'is_deleted'),
                name='inventory_material_project_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('project', 'material'),
                condition=Q(is_deleted=False, material__isnull=False),
                name='inventory_unique_active_project_material',
            ),
            models.CheckConstraint(
                condition=Q(stock__gte=0),
                name='inventory_material_stock_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(quantity_used__gte=0),
                name='inventory_material_used_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(quantity_used__lte=models.F('stock')),
                name='inventory_material_used_lte_stock',
            ),
        ]

    def __str__(self) -> str:
        material_name = self.material.name if self.material else 'Unspecified'
        return f'{self.project.project_name} {material_name}'

    @property
    def available_stock(self):
        return self.stock - self.quantity_used

    def clean(self):
        super().clean()
        errors = {}
        if self.stock is not None and self.stock < 0:
            errors['stock'] = 'Stock tidak boleh negatif.'
        if self.quantity_used is not None and self.quantity_used < 0:
            errors['quantity_used'] = 'Quantity used tidak boleh negatif.'
        if (
            self.stock is not None
            and self.quantity_used is not None
            and self.quantity_used > self.stock
        ):
            errors['quantity_used'] = (
                'Quantity used tidak boleh melebihi stock.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class Tool(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(ToolCategory, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to=upload_tools, null=True, blank=True)
    serial_number = models.CharField(max_length=255)
    conditions = models.TextField()
    amount = models.PositiveIntegerField()
    available = models.PositiveIntegerField(default=0, editable=False)
    is_under_maintenance = models.BooleanField(default=False)
    maintenance_interval_days = models.PositiveIntegerField(
        default=90
    )
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name='inventory_tool_amount_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(available__gte=0),
                name='inventory_tool_available_nonnegative',
            ),
            models.CheckConstraint(
                condition=Q(available__lte=models.F('amount')),
                name='inventory_tool_available_lte_amount',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def recalculate_available(self, using=None):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            locked_tool = Tool.all_objects.using(database).select_for_update().get(
                pk=self.pk
            )
            allocated = (
                ToolOnProject.objects.using(database)
                .filter(tool_id=self.pk, returned_date__isnull=True)
                .aggregate(value=Sum('amount'))['value']
                or 0
            )
            if allocated > locked_tool.amount:
                raise ValidationError(
                    {
                        'amount': (
                            f'Total alat yang sedang dipakai ({allocated}) '
                            f'melebihi jumlah alat ({locked_tool.amount}).'
                        )
                    }
                )
            available = (
                0
                if locked_tool.is_under_maintenance
                else locked_tool.amount - allocated
            )
            Tool.all_objects.using(database).filter(pk=self.pk).update(
                available=available
            )
            self.available = available
        return available

    def save(self, *args, **kwargs):
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        with transaction.atomic(using=database):
            self.available = self.amount
            self.full_clean()
            result = super().save(*args, **kwargs)
            self.recalculate_available(using=database)
        return result

class ToolOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_tools')
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='tools_project')
    amount = models.PositiveIntegerField()
    assigned_date = models.DateField()
    returned_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'returned_date', 'is_deleted'),
                name='inventory_tool_project_idx',
            ),
            models.Index(
                fields=('tool', 'returned_date', 'is_deleted'),
                name='inventory_tool_active_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='inventory_tool_assignment_amount_positive',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.tool.name} on {self.project.project_name}'

    def clean(self):
        super().clean()
        errors = {}
        if not self.amount or self.amount <= 0:
            errors['amount'] = 'Jumlah alat harus lebih dari 0.'
        if (
            self.returned_date
            and self.assigned_date
            and self.returned_date < self.assigned_date
        ):
            errors['returned_date'] = (
                'Tanggal kembali tidak boleh sebelum tanggal penugasan.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        affected_tool_ids = {self.tool_id}

        with transaction.atomic(using=database):
            if not self._state.adding:
                previous = ToolOnProject.all_objects.using(
                    database
                ).select_for_update().get(pk=self.pk)
                affected_tool_ids.add(previous.tool_id)

            self.full_clean()
            result = super().save(*args, **kwargs)
            for tool_id in affected_tool_ids:
                tool = Tool.all_objects.using(database).get(pk=tool_id)
                tool.recalculate_available(using=database)
        return result

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        tool = self.tool
        with transaction.atomic(using=database):
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            if result[0] and not tool.is_deleted:
                tool.recalculate_available(using=database)
        return result

    def restore(self, using=None, user=None, cascade_at=None):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        tool = self.tool
        with transaction.atomic(using=database):
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if not tool.is_deleted:
                tool.recalculate_available(using=database)
        return result


class StockMovementType(models.TextChoices):
    PURCHASE = 'purchase', 'Purchase'
    EXPENSE = 'expense', 'Expense'
    USAGE = 'usage', 'Usage'
    ADJUSTMENT = 'adjustment', 'Adjustment'
    TRANSFER = 'transfer', 'Transfer'
    RETURN = 'return', 'Return'


class StockMovement(AuditModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='stock_movements',
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='stock_movements',
    )
    movement_type = models.CharField(
        max_length=20, choices=StockMovementType.choices
    )
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    balance_after = models.DecimalField(
        max_digits=16, decimal_places=4, editable=False
    )
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(
                fields=('project', 'material', '-created_at'),
                name='inventory_stock_history_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(quantity=0),
                name='inventory_stock_movement_nonzero',
            ),
        ]

    def __str__(self):
        return f'{self.material} {self.quantity:+} ({self.movement_type})'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                'Stock movement bersifat immutable dan tidak dapat diubah.'
            )
        return super().save(*args, **kwargs)


class PurchaseRequestStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    ORDERED = 'ordered', 'Ordered'
    RECEIVED = 'received', 'Received'
    REJECTED = 'rejected', 'Rejected'
    CANCELLED = 'cancelled', 'Cancelled'


class PurchaseRequest(AuditModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='purchase_requests',
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='purchase_requests',
    )
    quantity = models.DecimalField(max_digits=16, decimal_places=4)
    status = models.CharField(
        max_length=20,
        choices=PurchaseRequestStatus.choices,
        default=PurchaseRequestStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_requests',
    )
    approved_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_purchase_requests',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(
                fields=('status', 'project', '-created_at'),
                name='inventory_purchase_queue_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name='inventory_purchase_quantity_positive',
            ),
        ]

    def clean(self):
        super().clean()
        if self.quantity is None or self.quantity <= 0:
            raise ValidationError(
                {'quantity': 'Quantity harus lebih besar dari 0.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.material} - {self.quantity} ({self.status})'


class ToolMaintenanceStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    IN_PROGRESS = 'in_progress', 'In progress'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class ToolMaintenance(AuditModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    tool = models.ForeignKey(
        Tool,
        on_delete=models.CASCADE,
        related_name='maintenance_records',
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ToolMaintenanceStatus.choices,
        default=ToolMaintenanceStatus.SCHEDULED,
    )
    cost = MoneyField(
        max_digits=16,
        decimal_places=2,
        default=0,
        default_currency='IDR',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ('-scheduled_date',)
        indexes = [
            models.Index(
                fields=('status', 'scheduled_date'),
                name='inv_maintenance_queue_idx',
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.completed_date
            and self.completed_date < self.scheduled_date
        ):
            raise ValidationError(
                {
                    'completed_date': (
                        'Tanggal selesai tidak boleh sebelum jadwal.'
                    )
                }
            )

    def _sync_tool_state(self, using):
        tool = Tool.all_objects.using(using).get(pk=self.tool_id)
        if tool.is_deleted:
            return
        active_statuses = {
            ToolMaintenanceStatus.SCHEDULED,
            ToolMaintenanceStatus.IN_PROGRESS,
        }
        has_active_maintenance = ToolMaintenance.objects.using(
            using
        ).filter(
            tool_id=self.tool_id,
            status__in=active_statuses,
        ).exists()
        Tool.all_objects.using(using).filter(pk=self.tool_id).update(
            is_under_maintenance=has_active_maintenance
        )
        tool.is_under_maintenance = has_active_maintenance
        tool.recalculate_available(using=using)

    def save(self, *args, **kwargs):
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        self.full_clean()
        with transaction.atomic(using=database):
            result = super().save(*args, **kwargs)
            self._sync_tool_state(database)
        return result

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            self._sync_tool_state(database)
        return result

    def restore(self, using=None, user=None, cascade_at=None):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            self._sync_tool_state(database)
        return result

    def __str__(self):
        return f'{self.tool} maintenance ({self.status})'
