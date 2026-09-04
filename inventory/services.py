from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    MaterialOnProject,
    PurchaseRequest,
    PurchaseRequestStatus,
    StockMovement,
    StockMovementType,
    Tool,
    ToolMaintenance,
    ToolMaintenanceStatus,
)


@transaction.atomic
def adjust_project_stock(
    project_id,
    material_id,
    delta,
    movement_type=StockMovementType.ADJUSTMENT,
    reference_type='',
    reference_id='',
    notes='',
):
    from project.models import Project

    delta = Decimal(str(delta))
    if delta == 0:
        return None

    Project.all_objects.select_for_update().get(pk=project_id)
    inventory = (
        MaterialOnProject.objects.select_for_update()
        .filter(project_id=project_id, material_id=material_id)
        .first()
    )
    if inventory is None:
        if delta < 0:
            raise ValidationError(
                'Stock material proyek tidak ditemukan untuk dikurangi.'
            )
        inventory = MaterialOnProject(
            project_id=project_id,
            material_id=material_id,
            stock=Decimal('0'),
            quantity_used=Decimal('0'),
            notes='Dibuat otomatis dari pergerakan stok.',
            approved_date=timezone.now(),
        )

    inventory.stock += delta
    if inventory.stock < inventory.quantity_used:
        raise ValidationError(
            'Perubahan membuat stock lebih kecil dari quantity used.'
        )
    inventory.save()

    StockMovement.objects.create(
        project_id=project_id,
        material_id=material_id,
        movement_type=movement_type,
        quantity=delta,
        balance_after=inventory.stock,
        reference_type=reference_type,
        reference_id=str(reference_id or ''),
        notes=notes,
    )
    return inventory


@transaction.atomic
def receive_purchase_request(purchase_request, actor):
    purchase_request = (
        PurchaseRequest.all_objects.select_for_update()
        .select_related('project', 'material')
        .get(pk=purchase_request.pk)
    )
    if purchase_request.status not in {
        PurchaseRequestStatus.APPROVED,
        PurchaseRequestStatus.ORDERED,
    }:
        raise ValidationError(
            'Hanya purchase request approved/ordered yang dapat diterima.'
        )

    adjust_project_stock(
        purchase_request.project_id,
        purchase_request.material_id,
        purchase_request.quantity,
        movement_type=StockMovementType.PURCHASE,
        reference_type='purchase_request',
        reference_id=purchase_request.pk,
        notes=purchase_request.notes,
    )
    purchase_request.status = PurchaseRequestStatus.RECEIVED
    purchase_request.received_at = timezone.now()
    purchase_request.save(update_fields=['status', 'received_at'])
    return purchase_request


@transaction.atomic
def complete_tool_maintenance(maintenance, actor=None):
    maintenance = (
        ToolMaintenance.all_objects.select_for_update()
        .select_related('tool')
        .get(pk=maintenance.pk)
    )
    completed_date = maintenance.completed_date or timezone.localdate()
    maintenance.status = ToolMaintenanceStatus.COMPLETED
    maintenance.completed_date = completed_date
    maintenance.save(update_fields=['status', 'completed_date'])

    tool = Tool.all_objects.select_for_update().get(pk=maintenance.tool_id)
    tool.is_under_maintenance = False
    tool.last_maintenance_date = completed_date
    tool.next_maintenance_date = completed_date + timedelta(
        days=tool.maintenance_interval_days
    )
    tool.save()
    return maintenance


@transaction.atomic
def create_low_stock_purchase_requests():
    created = []
    inventories = MaterialOnProject.objects.select_related(
        'material', 'project'
    ).filter(material__minimum_stock__gt=0)
    for inventory in inventories.iterator(chunk_size=200):
        shortage = inventory.material.minimum_stock - inventory.available_stock
        if shortage <= 0:
            continue
        exists = PurchaseRequest.objects.filter(
            project=inventory.project,
            material=inventory.material,
            status__in=[
                PurchaseRequestStatus.PENDING,
                PurchaseRequestStatus.APPROVED,
                PurchaseRequestStatus.ORDERED,
            ],
        ).exists()
        if exists:
            continue
        created.append(
            PurchaseRequest.objects.create(
                project=inventory.project,
                material=inventory.material,
                quantity=shortage,
                notes='Dibuat otomatis karena stock di bawah minimum.',
            )
        )
    return created


@transaction.atomic
def schedule_due_tool_maintenance(target_date=None):
    target_date = target_date or timezone.localdate()
    created = []
    tools = Tool.objects.filter(
        next_maintenance_date__lte=target_date,
        is_under_maintenance=False,
    )
    for tool in tools.select_for_update():
        maintenance, was_created = ToolMaintenance.objects.get_or_create(
            tool=tool,
            scheduled_date=target_date,
            status=ToolMaintenanceStatus.SCHEDULED,
            defaults={'notes': 'Dijadwalkan otomatis.'},
        )
        if was_created:
            tool.is_under_maintenance = True
            tool.save(update_fields=['is_under_maintenance'])
            created.append(maintenance)
    return created
