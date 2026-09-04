from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.templatetags.static import static
from django.urls import reverse

from core.models import DocumentType
from finance.models import BillOfQuantity

from .models import (
    Document,
    DocumentStatus,
    DocumentVersion,
    ProgressReport,
    Project,
    ProjectStatus,
    Schedule,
    ScheduleStatusType,
)


class ProjectProgressTests(TestCase):
    def test_latest_report_per_boq_drives_project_progress(self):
        project = Project.objects.create(
            project_name='Progress Project',
            project_code='PRG-001',
            description='Automatic progress test',
            start_date=date(2026, 1, 1),
        )
        first_boq = BillOfQuantity.objects.create(
            project=project,
            document_name='BOQ A',
        )
        second_boq = BillOfQuantity.objects.create(
            project=project,
            document_name='BOQ B',
        )
        ProgressReport.objects.create(
            boq_item=first_boq,
            progress_number=1,
            report_date=date(2026, 1, 10),
            progress_percentage=20,
            notes='First',
        )
        ProgressReport.objects.create(
            boq_item=first_boq,
            progress_number=2,
            report_date=date(2026, 1, 17),
            progress_percentage=60,
            notes='Latest first BOQ',
        )
        ProgressReport.objects.create(
            boq_item=second_boq,
            progress_number=1,
            report_date=date(2026, 1, 17),
            progress_percentage=40,
            notes='Second BOQ',
        )

        project.refresh_from_db()
        self.assertEqual(project.progress, Decimal('50.00'))
        self.assertEqual(project.project_status, ProjectStatus.ON_GOING)

        latest = ProgressReport.objects.create(
            boq_item=second_boq,
            progress_number=2,
            report_date=date(2026, 1, 24),
            progress_percentage=100,
            notes='Second BOQ complete',
        )
        project.refresh_from_db()
        self.assertEqual(project.progress, Decimal('80.00'))

        latest.delete()
        project.refresh_from_db()
        self.assertEqual(project.progress, Decimal('50.00'))


class ProgressReportAdminVisualTests(TestCase):
    def test_changelist_compares_actual_progress_with_timeline(self):
        user = User.objects.create_superuser(
            username='progress-visual-admin',
            email='progress-visual@example.com',
            password='test-password',
        )
        project = Project.objects.create(
            project_name='Timeline Comparison',
            project_code='TIME-001',
            description='Progress comparison',
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        boq = BillOfQuantity.objects.create(
            project=project,
            document_name='Main Construction',
        )
        ProgressReport.objects.create(
            boq_item=boq,
            progress_number=1,
            report_date=date(2026, 7, 20),
            progress_percentage=42,
            notes='Actual progress',
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse('admin:project_progressreport_changelist'),
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PROJECT PERFORMANCE')
        self.assertContains(response, 'Progres aktual vs timeline')
        self.assertContains(response, 'TIME-001')
        self.assertContains(response, 'mmg-progress-cell')


class ProjectShowcaseAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='project-showcase-admin',
            email='showcase@example.com',
            password='test-password',
        )
        self.project = Project.objects.create(
            project_name='Showcase Client Villa',
            project_code='SCV-001',
            description=(
                'Hunian tropis kontemporer yang mengutamakan kualitas '
                'ruang, cahaya alami, dan ketelitian konstruksi.'
            ),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            progress=Decimal('42.00'),
        )
        document_type = DocumentType.objects.create(
            name='Client Progress Document'
        )
        document = Document.objects.create(
            project=self.project,
            document_type=document_type,
            document_name='Weekly Report 08',
            status=DocumentStatus.IN_REVIEW,
            issue_date=date(2026, 7, 20),
            due_date=date(2026, 7, 27),
        )
        DocumentVersion.objects.create(
            document=document,
            title='Weekly Report 08',
            document_file='document_project/weekly-report-08.pdf',
            document_number='SCV-WPR-008',
            status=DocumentStatus.IN_REVIEW,
            notes='Client presentation test.',
        )
        self.client.force_login(self.superuser)

    def test_project_admin_renders_showcase_and_presentation_mode(self):
        changelist = self.client.get(
            reverse('admin:project_project_changelist'),
            secure=True,
        )
        change_page = self.client.get(
            reverse(
                'admin:project_project_change',
                args=(self.project.pk,),
            ),
            secure=True,
        )
        presentation = self.client.get(
            reverse(
                'admin:project_project_presentation',
                args=(self.project.pk,),
            ),
            secure=True,
        )

        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, 'Portofolio proyek')
        self.assertContains(changelist, self.project.project_name)
        self.assertContains(changelist, '42%')
        self.assertContains(
            changelist,
            static('admin/css/project_showcase.css'),
        )

        self.assertEqual(change_page.status_code, 200)
        self.assertContains(change_page, 'PROJECT PULSE')
        self.assertContains(change_page, 'Mode presentasi')
        self.assertContains(change_page, 'id_presentation_image')

        self.assertEqual(presentation.status_code, 200)
        self.assertContains(presentation, self.project.project_name)
        self.assertContains(presentation, 'Cetak / Simpan PDF')
        self.assertContains(presentation, 'PROGRESS OVERVIEW')
        self.assertContains(presentation, self.project.description)
        self.assertContains(presentation, 'Latest issue register')
        self.assertContains(presentation, 'Weekly Report 08')
        self.assertContains(presentation, 'SCV-WPR-008')


class DocumentExplorerAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='document-explorer-admin',
            email='document-explorer@example.com',
            password='test-password',
        )
        self.first_project = Project.objects.create(
            project_name='Niskala Courtyard',
            project_code='NCV-001',
            description='Document explorer project',
            start_date=date(2026, 1, 1),
        )
        self.second_project = Project.objects.create(
            project_name='Uluwatu Residence',
            project_code='ULU-002',
            description='Second document explorer project',
            start_date=date(2026, 2, 1),
        )
        self.drawing_type, _ = DocumentType.objects.get_or_create(
            name='Architectural Drawing'
        )
        self.contract_type, _ = DocumentType.objects.get_or_create(
            name='Contract Agreement'
        )
        self.drawing = Document.objects.create(
            project=self.first_project,
            document_type=self.drawing_type,
            document_name='Pool Detail',
            status=DocumentStatus.APPROVED,
            issue_date=date(2026, 7, 20),
            due_date=date(2026, 7, 27),
        )
        DocumentVersion.objects.create(
            document=self.drawing,
            title='Pool Detail Rev 02',
            document_file='document_project/pool-detail-r02.pdf',
            document_number='NCV-ARC-DTL-034',
            status=DocumentStatus.APPROVED,
            notes='Approved client drawing.',
        )
        contract = Document.objects.create(
            project=self.second_project,
            document_type=self.contract_type,
            document_name='Main Contract',
            status=DocumentStatus.IN_REVIEW,
            issue_date=date(2026, 7, 21),
            due_date=date(2026, 7, 28),
        )
        DocumentVersion.objects.create(
            document=contract,
            title='Main Contract Draft',
            document_file='document_project/main-contract.docx',
            document_number='ULU-CON-001',
            status=DocumentStatus.IN_REVIEW,
            notes='Contract review.',
        )
        self.client.force_login(self.superuser)
        self.changelist_url = reverse(
            'admin:project_document_changelist'
        )
        self.explorer_url = reverse(
            'admin:project_document_explorer'
        )

    def test_document_changelist_opens_project_folder_explorer(self):
        response = self.client.get(self.changelist_url, secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Document Explorer')
        self.assertContains(response, 'Niskala Courtyard')
        self.assertContains(response, 'Uluwatu Residence')
        self.assertContains(
            response,
            static('admin/css/document_explorer.css'),
        )

    def test_explorer_navigates_project_type_and_latest_file(self):
        project_folder = self.client.get(
            self.explorer_url,
            {'project': str(self.first_project.pk)},
            secure=True,
        )
        file_view = self.client.get(
            self.explorer_url,
            {
                'project': str(self.first_project.pk),
                'document_type': str(self.drawing_type.pk),
            },
            secure=True,
        )

        self.assertEqual(project_folder.status_code, 200)
        self.assertContains(project_folder, 'Architectural Drawing')
        self.assertEqual(file_view.status_code, 200)
        self.assertContains(file_view, 'Pool Detail')
        self.assertContains(file_view, 'NCV-ARC-DTL-034')
        self.assertContains(file_view, 'Pool Detail Rev 02')
        self.assertContains(
            file_view,
            '/media/document_project/pool-detail-r02.pdf',
        )

    def test_explorer_can_group_by_document_type_and_search_versions(self):
        grouped = self.client.get(
            self.explorer_url,
            {'group_by': 'type'},
            secure=True,
        )
        searched = self.client.get(
            self.explorer_url,
            {'q': 'NCV-ARC-DTL-034'},
            secure=True,
        )

        self.assertEqual(grouped.status_code, 200)
        self.assertContains(grouped, 'Architectural Drawing')
        self.assertContains(grouped, 'Contract Agreement')
        self.assertEqual(searched.status_code, 200)
        self.assertContains(searched, 'Pool Detail')
        self.assertNotContains(searched, 'Main Contract')

    def test_legacy_table_view_remains_available(self):
        response = self.client.get(
            self.changelist_url,
            {'view': 'list'},
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Document Explorer')
        self.assertContains(response, 'Pool Detail')
        self.assertContains(response, self.explorer_url)


class ScheduleCalendarAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='schedule-calendar-admin',
            email='schedule-calendar@example.com',
            password='test-password',
        )
        self.first_project = Project.objects.create(
            project_name='Calendar Villa',
            project_code='CAL-001',
            description='Calendar project',
            start_date=date(2026, 7, 1),
        )
        self.second_project = Project.objects.create(
            project_name='Calendar Office',
            project_code='CAL-002',
            description='Second calendar project',
            start_date=date(2026, 7, 1),
        )
        first_boq = BillOfQuantity.objects.create(
            project=self.first_project,
            document_name='Structural Works',
        )
        second_boq = BillOfQuantity.objects.create(
            project=self.second_project,
            document_name='MEP Works',
        )
        self.first_schedule = Schedule.objects.create(
            boq_item=first_boq,
            duration=10,
            start_date=date(2026, 7, 6),
            end_date=date(2026, 7, 15),
            status=ScheduleStatusType.IN_PROGRESS,
            notes='Structure zone A',
            attachment='schedule_attachment_photo/structure.pdf',
        )
        Schedule.objects.create(
            boq_item=second_boq,
            duration=5,
            start_date=date(2026, 7, 20),
            end_date=date(2026, 7, 24),
            status=ScheduleStatusType.COMPLETED,
            notes='MEP rough in',
            attachment='schedule_attachment_photo/mep.pdf',
        )
        self.client.force_login(self.superuser)
        self.changelist_url = reverse(
            'admin:project_schedule_changelist'
        )
        self.calendar_url = reverse(
            'admin:project_schedule_calendar'
        )
        self.list_url = reverse('admin:project_schedule_list')

    def test_changelist_defaults_to_calendar(self):
        response = self.client.get(self.changelist_url, secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule Calendar')
        self.assertContains(response, 'List View')
        self.assertContains(response, self.list_url)
        self.assertNotContains(response, 'unfold-filter-autocomplete')

    def test_list_view_remains_available_with_searchable_project_filter(self):
        response = self.client.get(self.list_url, secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calendar View')
        self.assertContains(response, self.calendar_url)
        self.assertContains(response, 'unfold-filter-autocomplete')
        self.assertContains(response, 'Apply Filters')
        self.assertContains(response, 'mmg-status-badge--danger')
        self.assertContains(response, 'CAL-001')

    def test_calendar_provides_agenda_fallback_for_small_screens(self):
        """Grid tujuh kolom tidak muat di ponsel, jadi view harus menyediakan
        daftar agenda datar sebagai penggantinya."""
        response = self.client.get(
            self.calendar_url,
            {'month': '2026-07'},
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        agenda = response.context['agenda']
        names = [
            item['schedule'].boq_item.document_name for item in agenda
        ]
        self.assertIn('Structural Works', names)
        self.assertIn('MEP Works', names)
        self.assertContains(response, 'mmg-calendar-agenda-row')
        for item in agenda:
            self.assertIn('tone', item)
            self.assertIn('change_url', item)

    def test_calendar_agenda_marks_schedules_crossing_month_boundary(self):
        """Agenda kehilangan konteks kalau tidak menandai pekerjaan yang
        mulai sebelum atau berakhir sesudah bulan yang dibuka."""
        spanning_boq = BillOfQuantity.objects.create(
            project=self.first_project,
            document_name='Spanning Works',
        )
        Schedule.objects.create(
            boq_item=spanning_boq,
            duration=90,
            start_date=date(2026, 6, 10),
            end_date=date(2026, 8, 20),
            status=ScheduleStatusType.IN_PROGRESS,
            notes='Melewati batas bulan',
            attachment='schedule_attachment_photo/spanning.pdf',
        )

        response = self.client.get(
            self.calendar_url,
            {'month': '2026-07'},
            secure=True,
        )

        agenda = {
            item['schedule'].boq_item.document_name: item
            for item in response.context['agenda']
        }
        spanning = agenda['Spanning Works']
        self.assertTrue(spanning['starts_before'])
        self.assertTrue(spanning['ends_after'])

        contained = agenda['Structural Works']
        self.assertFalse(contained['starts_before'])
        self.assertFalse(contained['ends_after'])

    def test_calendar_renders_month_events_and_project_scope(self):
        response = self.client.get(
            self.calendar_url,
            {'month': '2026-07'},
            secure=True,
        )
        filtered = self.client.get(
            self.calendar_url,
            {
                'month': '2026-07',
                'project': str(self.first_project.pk),
            },
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Juli 2026')
        self.assertContains(response, 'Structural Works')
        self.assertContains(response, 'MEP Works')
        self.assertContains(
            response,
            static('admin/css/schedule_calendar.css'),
        )
        self.assertContains(
            response,
            reverse(
                'admin:project_schedule_change',
                args=(self.first_schedule.pk,),
            ),
        )
        self.assertContains(
            response,
            f'data-schedule-id="{self.first_schedule.pk}"',
            count=2,
        )
        self.assertContains(response, 'continues-after')
        self.assertContains(response, 'continues-before')

        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, 'CAL-001 · Calendar Villa')
        self.assertContains(filtered, 'Structural Works')
        self.assertNotContains(filtered, 'MEP Works')

    def test_calendar_ignores_invalid_month_and_project_parameters(self):
        response = self.client.get(
            self.calendar_url,
            {'month': 'not-a-month', 'project': 'not-a-uuid'},
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Schedule Calendar')
