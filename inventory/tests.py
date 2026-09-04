from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import MaterialCategory, ToolCategory, UnitType
from project.models import Project

from .models import (
    Material,
    MaterialOnProject,
    PurchaseRequest,
    PurchaseRequestStatus,
    StockMovement,
    Tool,
    ToolMaintenance,
    ToolMaintenanceStatus,
    ToolOnProject,
)
from .services import (
    complete_tool_maintenance,
    create_low_stock_purchase_requests,
    receive_purchase_request,
    schedule_due_tool_maintenance,
)


class ToolAvailabilityTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_name='Tool Project',
            project_code='TOOL-001',
            description='Tool availability tests',
            start_date=date(2025, 1, 1),
        )
        self.category = ToolCategory.objects.create(name='Test Tool')
        self.tool = Tool.objects.create(
            category=self.category,
            name='Test Drill',
            serial_number='DRILL-001',
            conditions='Good',
            amount=5,
        )

    def test_assignment_and_return_recalculate_available(self):
        assignment = ToolOnProject.objects.create(
            project=self.project,
            tool=self.tool,
            amount=2,
            assigned_date=date(2025, 1, 2),
        )
        self.tool.refresh_from_db()
        self.assertEqual(self.tool.available, 3)

        assignment.returned_date = date(2025, 1, 3)
        assignment.save()
        self.tool.refresh_from_db()
        self.assertEqual(self.tool.available, 5)

    def test_over_allocation_is_rejected_atomically(self):
        ToolOnProject.objects.create(
            project=self.project,
            tool=self.tool,
            amount=3,
            assigned_date=date(2025, 1, 2),
        )

        with self.assertRaises(ValidationError):
            ToolOnProject.objects.create(
                project=self.project,
                tool=self.tool,
                amount=3,
                assigned_date=date(2025, 1, 2),
            )

        self.tool.refresh_from_db()
        self.assertEqual(self.tool.available, 2)

    def test_project_soft_delete_and_restore_recalculate_available(self):
        assignment = ToolOnProject.objects.create(
            project=self.project,
            tool=self.tool,
            amount=2,
            assigned_date=date(2025, 1, 2),
        )

        self.project.delete()
        self.tool.refresh_from_db()
        self.assertEqual(self.tool.available, 5)
        self.assertFalse(
            ToolOnProject.objects.filter(pk=assignment.pk).exists()
        )

        Project.all_objects.get(pk=self.project.pk).restore()
        self.tool.refresh_from_db()
        self.assertEqual(self.tool.available, 3)
        self.assertTrue(
            ToolOnProject.objects.filter(pk=assignment.pk).exists()
        )


class InventoryAutomationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            project_name='Inventory Project',
            project_code='INV-001',
            description='Inventory automation tests',
            start_date=date(2026, 1, 1),
        )
        self.material_category = MaterialCategory.objects.create(
            name='Inventory Category'
        )
        self.unit = UnitType.objects.create(name='Inventory Unit')
        self.material = Material.objects.create(
            category=self.material_category,
            unit=self.unit,
            code='AUTO-MAT',
            name='Automatic Material',
            minimum_stock=Decimal('10'),
            descriptions='Test',
        )
        self.inventory = MaterialOnProject.objects.create(
            project=self.project,
            material=self.material,
            stock=Decimal('4'),
            quantity_used=Decimal('1'),
            notes='Low stock',
        )

    def test_low_stock_request_is_idempotent_and_receipt_updates_stock(self):
        created = create_low_stock_purchase_requests()
        self.assertEqual(len(created), 1)
        purchase = created[0]
        self.assertEqual(purchase.quantity, Decimal('7'))
        self.assertEqual(create_low_stock_purchase_requests(), [])

        purchase.status = PurchaseRequestStatus.APPROVED
        purchase.save()
        receive_purchase_request(purchase, actor=None)
        self.inventory.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(self.inventory.stock, Decimal('11'))
        self.assertEqual(purchase.status, PurchaseRequestStatus.RECEIVED)
        self.assertTrue(
            StockMovement.objects.filter(
                reference_id=str(purchase.pk),
                quantity=Decimal('7'),
            ).exists()
        )

    def test_maintenance_locks_and_releases_tool(self):
        category = ToolCategory.objects.create(name='Maintenance Tool')
        tool = Tool.objects.create(
            category=category,
            name='Service Drill',
            serial_number='SERVICE-001',
            conditions='Good',
            amount=3,
            maintenance_interval_days=30,
            next_maintenance_date=date(2026, 1, 1),
        )
        maintenance = schedule_due_tool_maintenance(date(2026, 1, 2))[0]
        tool.refresh_from_db()
        self.assertTrue(tool.is_under_maintenance)
        self.assertEqual(tool.available, 0)

        complete_tool_maintenance(maintenance)
        tool.refresh_from_db()
        maintenance.refresh_from_db()
        self.assertEqual(
            maintenance.status, ToolMaintenanceStatus.COMPLETED
        )
        self.assertFalse(tool.is_under_maintenance)
        self.assertEqual(tool.available, 3)
        self.assertEqual(
            tool.next_maintenance_date,
            maintenance.completed_date + timedelta(days=30),
        )


class InventoryAdminVisualTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='inventory-visual-admin',
            email='inventory-visual@example.com',
            password='test-password',
        )
        self.project = Project.objects.create(
            project_name='Visual Inventory',
            project_code='VIS-INV',
            description='Inventory visual indicators',
            start_date=date(2026, 1, 1),
        )
        category = MaterialCategory.objects.create(
            name='Visual Material'
        )
        unit, _ = UnitType.objects.get_or_create(name='Visual Bag')
        material = Material.objects.create(
            category=category,
            unit=unit,
            code='VIS-MAT',
            name='Visual Cement',
            minimum_stock=Decimal('10'),
            descriptions='Low stock visual',
        )
        MaterialOnProject.objects.create(
            project=self.project,
            material=material,
            stock=Decimal('5'),
            quantity_used=Decimal('2'),
            notes='Needs replenishment',
        )
        tool_category = ToolCategory.objects.create(name='Visual Tool')
        Tool.objects.create(
            category=tool_category,
            name='Visual Drill',
            serial_number='VIS-TOOL',
            conditions='Good',
            amount=4,
        )
        self.client.force_login(self.user)

    def test_stock_and_tool_lists_show_operational_indicators(self):
        stock_response = self.client.get(
            reverse('admin:inventory_materialonproject_changelist'),
            secure=True,
        )
        tool_response = self.client.get(
            reverse('admin:inventory_tool_changelist'),
            secure=True,
        )

        self.assertEqual(stock_response.status_code, 200)
        self.assertContains(stock_response, 'mmg-stock-indicator--danger')
        self.assertContains(stock_response, 'Stok rendah')
        self.assertEqual(tool_response.status_code, 200)
        self.assertContains(tool_response, 'mmg-utilization')
        self.assertContains(tool_response, 'tersedia')
