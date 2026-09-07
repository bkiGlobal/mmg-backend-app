from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from unfold.admin import ModelAdmin
from PIL import Image

from finance.models import (
    BillOfQuantity,
    BillOfQuantityVersion,
    ExpenseOnProject,
    FinanceData,
    PaymentRequest,
    PettyCash,
)
from finance.views import FinanceDataModelViewSet
from inventory.models import (
    MaterialOnProject,
    PurchaseRequest,
    StockMovement,
    ToolOnProject,
)
from project.models import (
    Defect,
    Document,
    Drawing,
    ErrorLog,
    ProgressReport,
    Project,
    Schedule,
    WorkMethod,
)
from team.models import (
    GenderType,
    LeaveRequest,
    LeaveStatus,
    Notifications,
    Profile,
    RoleType,
    Signature,
    StatusType,
)

from .models import ApprovalStatus
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from .crons import (
    CronJobAlreadyRunning,
    cron_job_lock,
    process_export_queue,
    run_daily_operations,
)
from .media import resolve_media_path, serve_media
from .storages import ForgivingManifestStaticFilesStorage
from .workflows import decide_approval, submit_for_approval


def create_profile(username, role):
    user = User.objects.create_user(
        username=username,
        password='test-password',
    )
    profile = Profile.objects.create(
        user=user,
        full_name=username.title(),
        role=role,
        gender=GenderType.MALE,
        status=StatusType.PERMANENT,
        birthday=date(1990, 1, 1),
        join_date=date(2024, 1, 1),
        phone_number=f'08{User.objects.count():09d}',
    )
    return user, profile


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.requester, self.requester_profile = create_profile(
            'requester', RoleType.WORKER
        )
        self.approver, self.approver_profile = create_profile(
            'approver', RoleType.PROJECT_ADMIN
        )
        self.leave = LeaveRequest.objects.create(
            user=self.requester_profile,
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 4),
            reason='Annual leave',
        )

    def test_submit_and_approve_updates_target_and_audit_trail(self):
        with self.captureOnCommitCallbacks(execute=True):
            approval = submit_for_approval(
                self.leave,
                self.requester,
                workflow_type='leave_request',
                required_role='project_admin',
            )
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        self.assertEqual(approval.events.count(), 1)
        self.assertTrue(
            Notifications.objects.filter(
                user=self.approver_profile,
                category='approval',
            ).exists()
        )

        with self.captureOnCommitCallbacks(execute=True):
            approval = decide_approval(
                approval,
                self.approver,
                approve=True,
                comment='Approved',
            )
        self.leave.refresh_from_db()
        self.assertEqual(approval.status, ApprovalStatus.APPROVED)
        self.assertEqual(self.leave.status, LeaveStatus.APPROVED)
        self.assertEqual(self.leave.approved_by, self.approver_profile)
        self.assertEqual(approval.events.count(), 2)

    def test_unprivileged_user_cannot_decide(self):
        approval = submit_for_approval(
            self.leave,
            self.requester,
            workflow_type='leave_request',
            required_role='project_admin',
        )
        with self.assertRaises(PermissionDenied):
            decide_approval(approval, self.requester, approve=True)

    def test_approved_boq_is_synchronized_to_document_register(self):
        project = Project.objects.create(
            project_name='Approval Project',
            project_code='APR-001',
            description='Document sync test',
            start_date=date(2026, 1, 1),
        )
        boq = BillOfQuantity.objects.create(
            project=project,
            document_name='BOQ Approval',
            issue_date=date(2026, 1, 2),
            due_date=None,
        )
        version = BillOfQuantityVersion.objects.create(
            boq=boq,
            title='BOQ Version 1',
            boq_file='boq_project/test.pdf',
            document_number='BOQ-001',
            notes='Ready for approval',
        )
        approval = submit_for_approval(
            boq,
            self.requester,
            workflow_type='bill_of_quantity',
            required_role='project_admin',
        )

        decide_approval(approval, self.approver, approve=True)
        boq.refresh_from_db()
        version.refresh_from_db()
        document = Document.objects.get(
            project=project,
            document_name='BOQ Approval',
        )

        self.assertEqual(boq.status, 'approved')
        self.assertEqual(version.status, 'approved')
        self.assertEqual(document.due_date, boq.issue_date)
        self.assertTrue(
            document.versions.filter(document_number='BOQ-001').exists()
        )


class EncryptedMediaAdminTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.user, self.profile = create_profile(
            'encrypted-owner',
            RoleType.WORKER,
        )
        image = Image.new('RGB', (32, 16), color=(20, 30, 40))
        content = BytesIO()
        image.save(content, format='PNG')
        self.signature = Signature.objects.create(
            user=self.profile,
            signature=SimpleUploadedFile(
                'signature.png',
                content.getvalue(),
                content_type='image/png',
            ),
        )

    def test_owner_can_preview_decrypted_image(self):
        self.client.force_login(self.user)
        response = self.client.get(
            self.signature.signature.url,
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        with Image.open(BytesIO(response.content)) as image:
            self.assertEqual(image.format, 'JPEG')

    def test_anonymous_and_other_user_cannot_preview(self):
        anonymous_response = self.client.get(
            self.signature.signature.url,
            secure=True,
        )
        self.assertEqual(anonymous_response.status_code, 302)

        other_user, _ = create_profile('encrypted-other', RoleType.WORKER)
        self.client.force_login(other_user)
        other_response = self.client.get(
            self.signature.signature.url,
            secure=True,
        )
        self.assertEqual(other_response.status_code, 404)


class ProjectScopeTests(TestCase):
    def test_finance_api_only_returns_accessible_projects(self):
        client_user, client = create_profile('client-a', RoleType.CLIENT)
        _, other_client = create_profile('client-b', RoleType.CLIENT)
        own_project = Project.objects.create(
            client=client,
            project_name='Visible',
            project_code='VISIBLE',
            description='Accessible project',
            start_date=date(2026, 1, 1),
        )
        other_project = Project.objects.create(
            client=other_client,
            project_name='Hidden',
            project_code='HIDDEN',
            description='Inaccessible project',
            start_date=date(2026, 1, 1),
        )
        FinanceData.objects.create(
            project=own_project,
            date=date(2026, 1, 1),
            description='Visible entry',
            debet=100,
            credit=0,
        )
        FinanceData.objects.create(
            project=other_project,
            date=date(2026, 1, 1),
            description='Hidden entry',
            debet=100,
            credit=0,
        )

        request = APIRequestFactory().get('/api/finance/finance-data/')
        force_authenticate(request, user=client_user)
        response = FinanceDataModelViewSet.as_view({'get': 'list'})(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['description'],
            'Visible entry',
        )

    def test_project_writer_cannot_create_finance_on_other_project(self):
        writer_user, writer = create_profile('project-qs', RoleType.QS)
        _, other_client = create_profile('other-owner', RoleType.CLIENT)
        Project.objects.create(
            client=writer,
            project_name='Assigned',
            project_code='ASSIGNED',
            description='Writer project',
            start_date=date(2026, 1, 1),
        )
        hidden = Project.objects.create(
            client=other_client,
            project_name='Not Assigned',
            project_code='NOT-ASSIGNED',
            description='Other project',
            start_date=date(2026, 1, 1),
        )
        request = APIRequestFactory().post(
            '/api/finance/finance-data/',
            {
                'project_id': str(hidden.pk),
                'date': '2026-01-01',
                'description': 'Unauthorized entry',
                'debet': '100.00',
                'credit': '0.00',
            },
            format='json',
        )
        force_authenticate(request, user=writer_user)
        response = FinanceDataModelViewSet.as_view({'post': 'create'})(
            request
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            FinanceData.objects.filter(
                description='Unauthorized entry'
            ).exists()
        )


class UnfoldAdminTests(TestCase):
    def test_dashboard_renders_and_all_admins_use_unfold(self):
        user = User.objects.create_superuser(
            username='admin-dashboard',
            email='admin@example.com',
            password='test-password',
        )
        self.client.force_login(user)
        response = self.client.get('/admin/', secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ringkasan operasional')
        self.assertContains(
            response,
            f'href="{static("favicon/MMG_PNG_WHITE.png")}"',
        )
        for admin_path in (
            '/admin/project/document/',
            '/admin/project/progressreport/',
            '/admin/inventory/materialonproject/',
            '/admin/inventory/tool/',
            '/admin/finance/pettycash/',
            '/admin/finance/billofquantity/',
            '/admin/finance/paymentrequest/',
            '/admin/team/leaverequest/',
            '/admin/team/workpolicy/',
            '/admin/team/holiday/',
            '/admin/core/location/',
        ):
            self.assertContains(response, f'href="{admin_path}"')
        for registered_admin in admin.site._registry.values():
            self.assertIsInstance(registered_admin, ModelAdmin)

    def test_approval_changelist_shows_pipeline(self):
        user = User.objects.create_superuser(
            username='approval-pipeline-admin',
            email='approval-pipeline@example.com',
            password='test-password',
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse('admin:core_approvalrequest_changelist'),
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'APPROVAL CONTROL')
        self.assertContains(response, 'Pipeline approval')
        self.assertContains(response, 'Pending')

    def test_project_related_admins_use_searchable_project_filter(self):
        request = RequestFactory().get('/admin/')
        project_filter_paths = {
            Document: 'project',
            Drawing: 'project',
            Defect: 'project',
            ErrorLog: 'project',
            WorkMethod: 'project',
            Schedule: 'boq_item__project',
            ProgressReport: 'boq_item__project',
            BillOfQuantity: 'project',
            PaymentRequest: 'project',
            ExpenseOnProject: 'project',
            FinanceData: 'project',
            PettyCash: 'project',
            MaterialOnProject: 'project',
            StockMovement: 'project',
            PurchaseRequest: 'project',
            ToolOnProject: 'project',
        }

        for model, field_path in project_filter_paths.items():
            model_admin = admin.site._registry[model]
            self.assertIn(
                (field_path, AutocompleteSelectFilter),
                model_admin.get_list_filter(request),
                msg=f'{model._meta.label} belum memakai project autocomplete.',
            )
            self.assertTrue(model_admin.list_filter_submit)

    def test_expense_tools_and_import_use_unfold_components(self):
        user = User.objects.create_superuser(
            username='admin-import',
            email='import@example.com',
            password='test-password',
        )
        self.client.force_login(user)

        changelist = self.client.get(
            '/admin/finance/expenseonproject/',
            secure=True,
        )
        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, 'Export Excel')
        self.assertContains(changelist, 'Import Excel')

        import_page = self.client.get(
            '/admin/finance/expenseonproject/import-all/',
            secure=True,
        )
        self.assertEqual(import_page.status_code, 200)
        self.assertContains(import_page, 'Unggah workbook expense')
        self.assertContains(import_page, 'Upload dan proses')

    def test_user_admin_exposes_unfold_password_change_form(self):
        admin_user = User.objects.create_superuser(
            username='admin-password',
            email='password-admin@example.com',
            password='test-password',
        )
        target_user = User.objects.create_user(
            username='field-user',
            password='old-password',
        )
        self.client.force_login(admin_user)

        change_page = self.client.get(
            reverse('admin:auth_user_change', args=(target_user.pk,)),
            {
                '_to_field': 'id',
                '_popup': '1',
            },
            secure=True,
        )

        self.assertEqual(change_page.status_code, 200)
        self.assertContains(change_page, 'href="../password/"')
        self.assertContains(change_page, 'mmg-password-change-button')
        self.assertContains(change_page, 'Ubah password')

        password_page = self.client.get(
            reverse(
                'admin:auth_user_password_change',
                args=(target_user.pk,),
            ),
            secure=True,
        )

        self.assertEqual(password_page.status_code, 200)
        self.assertContains(password_page, 'name="password1"')
        self.assertContains(password_page, 'name="password2"')


class LegacyMediaTests(SimpleTestCase):
    def test_media_falls_back_to_allowlisted_legacy_directory(self):
        with TemporaryDirectory() as media_root, TemporaryDirectory() as legacy:
            legacy_file = (
                Path(legacy)
                / 'finance_proof_photo'
                / 'proof.jpeg'
            )
            legacy_file.parent.mkdir()
            legacy_file.write_bytes(b'legacy-image')

            with override_settings(
                MEDIA_ROOT=media_root,
                LEGACY_MEDIA_ROOTS=[legacy],
                LEGACY_MEDIA_DIRECTORIES=['finance_proof_photo'],
            ):
                resolved = resolve_media_path(
                    'finance_proof_photo/proof.jpeg'
                )
                response = serve_media(
                    RequestFactory().get('/media/proof.jpeg'),
                    'finance_proof_photo/proof.jpeg',
                )

            self.assertEqual(resolved, legacy_file.resolve())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                b''.join(response.streaming_content),
                b'legacy-image',
            )

    def test_media_rejects_path_traversal_and_non_allowlisted_legacy(self):
        with TemporaryDirectory() as media_root, TemporaryDirectory() as legacy:
            private_file = Path(legacy) / 'private.txt'
            private_file.write_text('secret')
            with override_settings(
                MEDIA_ROOT=media_root,
                LEGACY_MEDIA_ROOTS=[legacy],
                LEGACY_MEDIA_DIRECTORIES=['finance_proof_photo'],
            ):
                self.assertIsNone(resolve_media_path('../private.txt'))
                self.assertIsNone(resolve_media_path('private.txt'))


@override_settings(DEBUG=False)
class StaffMediaRouteTests(TestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
            LEGACY_MEDIA_ROOTS=[],
        )
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        media_file = (
            Path(self.media_directory.name)
            / 'leave_request'
            / 'proof.jpeg'
        )
        media_file.parent.mkdir()
        media_file.write_bytes(b'private-image')
        self.media_url = '/media/leave_request/proof.jpeg'

    def test_staff_user_can_read_existing_media(self):
        staff = User.objects.create_user(
            username='media-staff',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(staff)

        response = self.client.get(self.media_url, secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            b''.join(response.streaming_content),
            b'private-image',
        )
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_anonymous_and_non_staff_users_are_redirected_to_admin_login(self):
        anonymous_response = self.client.get(self.media_url, secure=True)
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertTrue(
            anonymous_response.url.startswith('/admin/login/?next=')
        )

        user = User.objects.create_user(
            username='media-non-staff',
            password='test-password',
        )
        self.client.force_login(user)
        non_staff_response = self.client.get(self.media_url, secure=True)

        self.assertEqual(non_staff_response.status_code, 302)
        self.assertTrue(
            non_staff_response.url.startswith('/admin/login/?next=')
        )


class StaticStoragePermissionTests(SimpleTestCase):
    def test_static_files_remain_publicly_readable(self):
        with TemporaryDirectory() as static_root:
            storage = ForgivingManifestStaticFilesStorage(
                location=static_root,
                base_url='/static/',
            )

        self.assertEqual(storage.file_permissions_mode, 0o644)
        self.assertEqual(storage.directory_permissions_mode, 0o755)


class CronSchedulingTests(SimpleTestCase):
    def test_daily_job_cleans_database_connections(self):
        with TemporaryDirectory() as lock_dir, override_settings(
            CRON_LOCK_DIR=lock_dir,
        ), patch(
            'core.crons.run_daily_automations',
            return_value={'overdue_schedules': 2},
        ) as automation, patch(
            'core.crons.close_old_connections',
        ) as close_connections:
            result = run_daily_operations(date(2026, 7, 28))

        self.assertEqual(result, {'overdue_schedules': 2})
        automation.assert_called_once_with(date(2026, 7, 28))
        self.assertEqual(close_connections.call_count, 2)

    def test_export_job_passes_configured_limit(self):
        with TemporaryDirectory() as lock_dir, override_settings(
            CRON_LOCK_DIR=lock_dir,
        ), patch(
            'core.crons.process_queued_exports',
            return_value=['job-1'],
        ) as process_exports:
            result = process_export_queue(limit=10)

        self.assertEqual(result, ['job-1'])
        process_exports.assert_called_once_with(limit=10)

    def test_same_job_cannot_overlap(self):
        with TemporaryDirectory() as lock_dir, override_settings(
            CRON_LOCK_DIR=lock_dir,
        ):
            with cron_job_lock('daily_operations'):
                with self.assertRaises(CronJobAlreadyRunning):
                    run_daily_operations()
