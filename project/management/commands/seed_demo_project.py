from datetime import time, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from djmoney.money import Money

from core.models import (
    ApprovalRequest,
    Brand,
    DocumentType,
    ExpenseCategory,
    FinanceType,
    Location,
    MaterialCategory,
    PaymentVia,
    ToolCategory,
    UnitType,
    WorkType,
)
from core.workflows import submit_for_approval
from finance.models import (
    BillOfQuantity,
    BillOfQuantityVersion,
    DiscountType,
    ExpenseDetail,
    ExpenseForMaterial,
    ExpenseOnProject,
    FinanceData,
    PaymentRequest,
    PaymentRequestVersion,
    PettyCash,
)
from inventory.models import (
    Material,
    MaterialOnProject,
    PurchaseRequest,
    PurchaseRequestStatus,
    Tool,
    ToolMaintenance,
    ToolMaintenanceStatus,
    ToolOnProject,
)
from project.models import (
    ApprovalLevel,
    Defect,
    DefectDetail,
    Document,
    DocumentStatus,
    DocumentVersion,
    Drawing,
    DrawingVersion,
    DurationType,
    ErrorLog,
    ErrorLogDetail,
    ErrorLogStatus,
    ProgressReport,
    Project,
    ProjectStatus,
    Schedule,
    ScheduleStatusType,
    WorkMethod,
)
from team.models import (
    GenderType,
    NotificationCategory,
    Notifications,
    Profile,
    RoleType,
    StatusType,
    SubContractor,
    SubContractorOnProject,
    SubContractorWorker,
    Team,
    TeamMember,
    WorkPolicy,
)


DEMO_PROJECT_CODE = 'DEMO-NCV-001'
DEMO_PASSWORD = 'DemoMMG2026!'
DEMO_MARKER = '[DEMO NISKALA]'

ASSETS = {
    'hero': 'niskala_courtyard_hero.png',
    'blueprint': 'niskala_courtyard_blueprint.png',
    'progress': 'niskala_courtyard_progress.png',
}


class Command(BaseCommand):
    help = (
        'Membuat data demonstrasi proyek Niskala Courtyard Villas beserta '
        'tim, dokumen, progres, inventory, defect, dan transaksi keuangan.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh-media',
            action='store_true',
            help='Unggah ulang seluruh media demo yang sudah pernah dibuat.',
        )

    def handle(self, *args, **options):
        self.refresh_media = options['refresh_media']
        self.asset_dir = (
            Path(settings.BASE_DIR) / 'project' / 'demo_assets'
        )
        self.asset_paths = {
            key: self.asset_dir / filename
            for key, filename in ASSETS.items()
        }
        missing = [
            str(path)
            for path in self.asset_paths.values()
            if not path.exists()
        ]
        if missing:
            raise CommandError(
                'Aset demo tidak ditemukan:\n- ' + '\n- '.join(missing)
            )

        with transaction.atomic():
            references = self._seed_references()
            locations = self._seed_locations()
            policies = self._seed_work_policies(locations)
            profiles = self._seed_users_and_profiles(locations, policies)
            team = self._seed_team(profiles)
            project = self._seed_project(
                locations=locations,
                profiles=profiles,
                team=team,
            )
            self._seed_project_partners(project, locations)
            self._seed_documents(project, references)
            boqs = self._seed_boqs_and_progress(project)
            self._seed_schedules(boqs)
            self._seed_quality_records(project, references, profiles)
            materials = self._seed_material_master(references)
            self._seed_expenses_and_inventory(
                project,
                references,
                materials,
                profiles,
            )
            self._seed_tools(project, references)
            self._seed_finance(project, references)
            self._seed_notifications(project, profiles)
            self._seed_approvals(project, profiles)
            project.recalculate_progress()

        project.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            '\nData demo berhasil disiapkan.'
        ))
        self.stdout.write(
            f'Project : {project.project_code} — {project.project_name}'
        )
        self.stdout.write(f'Progress: {project.progress}%')
        self.stdout.write(
            'Admin   : /admin/project/project/'
        )
        self.stdout.write(
            'Login demo staff: demo_ayu_pm / ' + DEMO_PASSWORD
        )
        self.stdout.write(
            'Login demo client: demo_client_niskala / ' + DEMO_PASSWORD
        )
        self.stdout.write(
            self.style.WARNING(
                'Akun dan password tersebut hanya untuk data demonstrasi.'
            )
        )

    @staticmethod
    def _audit_defaults(defaults):
        return {
            **defaults,
            'is_deleted': False,
            'deleted_at': None,
            'deleted_by': None,
        }

    def _upsert(self, model, lookup, defaults):
        manager = getattr(model, 'all_objects', model.objects)
        return manager.update_or_create(
            **lookup,
            defaults=self._audit_defaults(defaults),
        )[0]

    def _asset(self, key, filename):
        return ContentFile(
            self.asset_paths[key].read_bytes(),
            name=filename,
        )

    def _save_with_asset(
        self,
        model,
        lookup,
        defaults,
        field_name,
        asset_key,
        filename,
    ):
        manager = getattr(model, 'all_objects', model.objects)
        obj = manager.filter(**lookup).first()
        created = obj is None
        if created:
            obj = model(**lookup)

        for field, value in self._audit_defaults(defaults).items():
            setattr(obj, field, value)

        current_file = getattr(obj, field_name, None)
        if created or self.refresh_media or not current_file:
            setattr(
                obj,
                field_name,
                self._asset(asset_key, filename),
            )
        obj.save()
        return obj

    @staticmethod
    def _location(name, longitude, latitude):
        point = Point(longitude, latitude, srid=4326)
        location = Location.objects.filter(name=name).first()
        if location is None:
            return Location.objects.create(name=name, address=point)
        location.address = point
        location.save()
        return location

    def _seed_references(self):
        def named(model, name):
            return model.objects.get_or_create(name=name)[0]

        return {
            'document_blueprint': named(
                DocumentType, 'Architectural Drawing'
            ),
            'document_contract': named(
                DocumentType, 'Contract Agreement'
            ),
            'document_progress': named(
                DocumentType, 'Weekly Progress Report'
            ),
            'document_safety': named(
                DocumentType, 'Safety Plan'
            ),
            'work_structure': named(WorkType, 'Structural Works'),
            'material_structural': named(
                MaterialCategory, 'Structural'
            ),
            'material_finishing': named(
                MaterialCategory, 'Finishing'
            ),
            'material_mep': named(MaterialCategory, 'MEP'),
            'tool_power': named(ToolCategory, 'Power Tool'),
            'tool_measuring': named(ToolCategory, 'Measuring'),
            'unit_kg': named(UnitType, 'kg'),
            'unit_bag': named(UnitType, 'bag'),
            'unit_m2': named(UnitType, 'm²'),
            'unit_m3': named(UnitType, 'm³'),
            'unit_lump_sum': named(UnitType, 'lump sum'),
            'brand_krakatau': named(Brand, 'Krakatau Steel'),
            'brand_tiga_roda': named(Brand, 'Tiga Roda'),
            'brand_local': named(Brand, 'Bali Artisan'),
            'expense_material': named(
                ExpenseCategory, 'Project Material'
            ),
            'expense_labor': named(
                ExpenseCategory, 'Site Labor'
            ),
            'expense_equipment': named(
                ExpenseCategory, 'Equipment Rental'
            ),
            'finance_project': named(
                FinanceType, 'Project Operations'
            ),
            'payment_transfer': named(
                PaymentVia, 'Bank Transfer'
            ),
        }

    def _seed_locations(self):
        return {
            'site': self._location(
                'Niskala Courtyard Villas — Ubud, Bali',
                115.2625,
                -8.5069,
            ),
            'office': self._location(
                'MMG Bali Project Office — Denpasar',
                115.2167,
                -8.6705,
            ),
            'client': self._location(
                'Client Residence — Sanur, Bali',
                115.2621,
                -8.6930,
            ),
            'staff_home': self._location(
                'Demo Staff Residence — Gianyar, Bali',
                115.3250,
                -8.5442,
            ),
            'subcontractor': self._location(
                'Workshop Batu Cakra — Gianyar, Bali',
                115.2941,
                -8.5327,
            ),
        }

    def _seed_work_policies(self, locations):
        site = self._upsert(
            WorkPolicy,
            {'name': 'Demo — Niskala Site'},
            {
                'office_location': locations['site'],
                'work_start': time(7, 30),
                'work_end': time(16, 30),
                'late_grace_minutes': 10,
                'overtime_after_minutes': 30,
                'geofence_radius_meters': 250,
                'allow_wfh': False,
                'wfh_geofence_radius_meters': 150,
                'workdays': [0, 1, 2, 3, 4, 5],
                'is_active': True,
            },
        )
        hybrid = self._upsert(
            WorkPolicy,
            {'name': 'Demo — Bali Hybrid'},
            {
                'office_location': locations['office'],
                'work_start': time(8, 30),
                'work_end': time(17, 30),
                'late_grace_minutes': 15,
                'overtime_after_minutes': 30,
                'geofence_radius_meters': 200,
                'allow_wfh': True,
                'wfh_geofence_radius_meters': 250,
                'workdays': [0, 1, 2, 3, 4],
                'is_active': True,
            },
        )
        return {'site': site, 'hybrid': hybrid}

    def _seed_users_and_profiles(self, locations, policies):
        today = timezone.localdate()
        people = [
            {
                'key': 'client',
                'username': 'demo_client_niskala',
                'email': 'client.niskala@example.test',
                'full_name': 'Adrian & Maya Wijaya',
                'first_name': 'Adrian',
                'last_name': 'Wijaya',
                'role': RoleType.CLIENT,
                'gender': GenderType.MALE,
                'status': StatusType.CLIENT,
                'birthday': today.replace(year=today.year - 43),
                'join_date': today - timedelta(days=180),
                'phone': '+62 811 9000 0101',
                'location': locations['client'],
                'policy': policies['hybrid'],
            },
            {
                'key': 'pm',
                'username': 'demo_ayu_pm',
                'email': 'ayu.pm@example.test',
                'full_name': 'Ayu Prameswari',
                'first_name': 'Ayu',
                'last_name': 'Prameswari',
                'role': RoleType.PM,
                'gender': GenderType.FEMALE,
                'status': StatusType.PERMANENT,
                'birthday': today.replace(year=today.year - 34),
                'join_date': today - timedelta(days=940),
                'phone': '+62 812 3100 1001',
                'location': locations['staff_home'],
                'policy': policies['site'],
            },
            {
                'key': 'architect',
                'username': 'demo_raka_architect',
                'email': 'raka.architect@example.test',
                'full_name': 'Raka Mahendra',
                'first_name': 'Raka',
                'last_name': 'Mahendra',
                'role': RoleType.ARCHITECT,
                'gender': GenderType.MALE,
                'status': StatusType.PERMANENT,
                'birthday': today.replace(year=today.year - 31),
                'join_date': today - timedelta(days=720),
                'phone': '+62 812 3100 1002',
                'location': locations['staff_home'],
                'policy': policies['hybrid'],
            },
            {
                'key': 'sm',
                'username': 'demo_dimas_sm',
                'email': 'dimas.site@example.test',
                'full_name': 'Dimas Wicaksana',
                'first_name': 'Dimas',
                'last_name': 'Wicaksana',
                'role': RoleType.SM,
                'gender': GenderType.MALE,
                'status': StatusType.PERMANENT,
                'birthday': today.replace(year=today.year - 38),
                'join_date': today - timedelta(days=1100),
                'phone': '+62 812 3100 1003',
                'location': locations['staff_home'],
                'policy': policies['site'],
            },
            {
                'key': 'qs',
                'username': 'demo_sari_qs',
                'email': 'sari.qs@example.test',
                'full_name': 'Sari Puspitasari',
                'first_name': 'Sari',
                'last_name': 'Puspitasari',
                'role': RoleType.QS,
                'gender': GenderType.FEMALE,
                'status': StatusType.PERMANENT,
                'birthday': today.replace(year=today.year - 29),
                'join_date': today - timedelta(days=480),
                'phone': '+62 812 3100 1004',
                'location': locations['staff_home'],
                'policy': policies['hybrid'],
            },
            {
                'key': 'logistic',
                'username': 'demo_bayu_logistic',
                'email': 'bayu.logistic@example.test',
                'full_name': 'Bayu Satriya',
                'first_name': 'Bayu',
                'last_name': 'Satriya',
                'role': RoleType.LOGISTIC,
                'gender': GenderType.MALE,
                'status': StatusType.CONTRACT,
                'birthday': today.replace(year=today.year - 27),
                'join_date': today - timedelta(days=310),
                'phone': '+62 812 3100 1005',
                'location': locations['staff_home'],
                'policy': policies['site'],
            },
            {
                'key': 'finance',
                'username': 'demo_eka_finance',
                'email': 'eka.finance@example.test',
                'full_name': 'Eka Lestari',
                'first_name': 'Eka',
                'last_name': 'Lestari',
                'role': RoleType.FINANCE_ADMIN,
                'gender': GenderType.FEMALE,
                'status': StatusType.PERMANENT,
                'birthday': today.replace(year=today.year - 32),
                'join_date': today - timedelta(days=620),
                'phone': '+62 812 3100 1006',
                'location': locations['staff_home'],
                'policy': policies['hybrid'],
            },
        ]

        staff_group, _ = Group.objects.get_or_create(
            name='Demo Project Staff'
        )
        staff_permissions = Permission.objects.filter(
            content_type__app_label__in=(
                'project',
                'finance',
                'inventory',
                'team',
            ),
            codename__startswith='view_',
        )
        staff_permissions = staff_permissions | Permission.objects.filter(
            content_type__app_label='team',
            codename__in=(
                'add_attendance',
                'change_attendance',
                'change_profile',
            ),
        )
        staff_group.permissions.set(staff_permissions.distinct())

        client_group, _ = Group.objects.get_or_create(
            name='Demo Project Client'
        )
        client_group.permissions.set(
            Permission.objects.filter(
                content_type__app_label='project',
                codename__in=(
                    'view_project',
                    'view_document',
                    'view_drawing',
                    'view_progressreport',
                    'view_schedule',
                ),
            )
        )

        user_model = get_user_model()
        profiles = {}
        for person in people:
            user, _ = user_model.objects.update_or_create(
                username=person['username'],
                defaults={
                    'email': person['email'],
                    'first_name': person['first_name'],
                    'last_name': person['last_name'],
                    'is_active': True,
                    'is_staff': True,
                    'is_superuser': False,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=['password'])
            user.groups.add(
                client_group if person['key'] == 'client' else staff_group
            )

            profile = self._upsert(
                Profile,
                {'user': user},
                {
                    'location': person['location'],
                    'full_name': person['full_name'],
                    'role': person['role'],
                    'gender': person['gender'],
                    'status': person['status'],
                    'birthday': person['birthday'],
                    'join_date': person['join_date'],
                    'phone_number': person['phone'],
                    'is_active': True,
                    'work_policy': person['policy'],
                },
            )
            profiles[person['key']] = profile
        return profiles

    def _seed_team(self, profiles):
        team = self._upsert(
            Team,
            {'name': 'Niskala Delivery Team'},
            {
                'description': (
                    f'{DEMO_MARKER} Tim lintas fungsi untuk delivery desain, '
                    'konstruksi, commercial, logistics, dan finance.'
                ),
            },
        )
        for profile in profiles.values():
            if profile.role == RoleType.CLIENT:
                continue
            self._upsert(
                TeamMember,
                {'team': team, 'user': profile},
                {'is_active': True},
            )
        return team

    def _seed_project(self, locations, profiles, team):
        today = timezone.localdate()
        project = self._save_with_asset(
            Project,
            {'project_code': DEMO_PROJECT_CODE},
            {
                'location': locations['site'],
                'client': profiles['client'],
                'project_name': 'Niskala Courtyard Villas',
                'team': team,
                'description': (
                    'Niskala Courtyard Villas adalah kompleks tiga vila '
                    'tropis premium yang berpusat pada courtyard dan '
                    'reflecting pool. Ruang lingkup mencakup struktur, '
                    'arsitektur, MEP, interior tetap, lanskap, serta '
                    'commissioning.\n\n'
                    'Fokus desainnya adalah material lokal yang tahan lama: '
                    'batu vulkanik Bali, screen kayu jati, ventilasi silang, '
                    'dan pencahayaan alami. Pekerjaan saat ini memasuki fase '
                    'arsitektur dan rough-in MEP dengan koordinasi mutu '
                    'mingguan bersama client.'
                ),
                'start_date': today - timedelta(days=150),
                'end_date': today + timedelta(days=110),
                'project_status': ProjectStatus.ON_GOING,
            },
            'presentation_image',
            'hero',
            'niskala-courtyard-villas.jpg',
        )
        return project

    def _seed_project_partners(self, project, locations):
        subcontractor = self._upsert(
            SubContractor,
            {'name': 'PT Cakra Batu Nusantara'},
            {
                'locations': locations['subcontractor'],
                'descriptions': (
                    f'{DEMO_MARKER} Spesialis pemasangan batu alam, kolam, '
                    'dan hardscape.'
                ),
                'contact_person': 'I Made Surya',
                'contact_number': '+62 812 7788 2201',
                'email': 'surya.cakrabatu@example.test',
            },
        )
        for name, phone in (
            ('I Kadek Bima', '+62 813 7000 2101'),
            ('Komang Arya', '+62 813 7000 2102'),
            ('Putu Yoga', '+62 813 7000 2103'),
        ):
            self._upsert(
                SubContractorWorker,
                {'subcon': subcontractor, 'worker_name': name},
                {'contact_number': phone},
            )
        self._upsert(
            SubContractorOnProject,
            {'project': project, 'subcon': subcontractor},
            {
                'is_active': True,
                'descriptions': (
                    'Paket pemasangan batu vulkanik, coping pool, dan '
                    'hardscape courtyard.'
                ),
            },
        )

    def _seed_documents(self, project, references):
        today = timezone.localdate()
        document_specs = (
            (
                'Kontrak Utama',
                references['document_contract'],
                DocumentStatus.APPROVED,
                'Kontrak konstruksi dan lampiran ruang lingkup.',
                'contract',
                'hero',
            ),
            (
                'Rencana HSE',
                references['document_safety'],
                DocumentStatus.APPROVED,
                'Rencana keselamatan, akses kerja, dan emergency response.',
                'hse',
                'progress',
            ),
            (
                'Laporan Mingguan 24',
                references['document_progress'],
                DocumentStatus.IN_REVIEW,
                'Ringkasan progres, kendala, keputusan, dan look-ahead.',
                'weekly-24',
                'progress',
            ),
        )
        for index, (
            name,
            document_type,
            status,
            notes,
            number,
            asset,
        ) in enumerate(document_specs, start=1):
            document = self._upsert(
                Document,
                {
                    'project': project,
                    'document_name': name,
                },
                {
                    'document_type': document_type,
                    'status': status,
                    'approval_required': True,
                    'approval_level': ApprovalLevel.LEVEL_1,
                    'issue_date': today - timedelta(days=30 - index),
                    'due_date': today + timedelta(days=index),
                },
            )
            self._save_with_asset(
                DocumentVersion,
                {
                    'document': document,
                    'document_number': (
                        f'NCV-DOC-{index:03d}-{number.upper()}'
                    ),
                },
                {
                    'title': name,
                    'status': status,
                    'notes': notes,
                    'comment': (
                        'Data demonstrasi untuk tampilan proyek berjalan.'
                    ),
                },
                'document_file',
                asset,
                f'{number}.jpg',
            )

        drawing_specs = (
            (
                'GA Courtyard',
                'NCV-ARC-GA-021',
                DocumentStatus.APPROVED,
                'General arrangement courtyard dan tiga villa wing.',
            ),
            (
                'Pool Detail',
                'NCV-ARC-DTL-034',
                DocumentStatus.IN_REVIEW,
                'Detail waterproofing, coping, dan overflow pool.',
            ),
        )
        for index, (name, number, status, notes) in enumerate(
            drawing_specs,
            start=1,
        ):
            drawing = self._upsert(
                Drawing,
                {'project': project, 'document_name': name},
                {
                    'drawing_type': references['document_blueprint'],
                    'status': status,
                    'issue_date': today - timedelta(days=18 - index),
                    'due_date': today + timedelta(days=7 + index),
                },
            )
            self._save_with_asset(
                DrawingVersion,
                {'drawing': drawing, 'document_number': number},
                {
                    'title': f'{name} — Revision C',
                    'status': status,
                    'notes': notes,
                    'comment': (
                        'Koordinasikan ukuran akhir dengan kondisi lapangan.'
                    ),
                },
                'drawing_file',
                'blueprint',
                f'{number.lower()}.jpg',
            )

        self._save_with_asset(
            WorkMethod,
            {
                'project': project,
                'document_number': 'NCV-MST-ARC-012',
            },
            {
                'work_title': 'Pemasangan Batu Vulkanik Courtyard',
                'notes': (
                    'Mockup wajib disetujui sebelum pemasangan massal. '
                    'Kontrol modul, warna, nat, dan perlindungan permukaan.'
                ),
            },
            'file',
            'progress',
            'method-statement-batu-vulkanik.jpg',
        )

    def _seed_boqs_and_progress(self, project):
        today = timezone.localdate()
        specs = (
            (
                'Structure & Civil',
                'NCV-BOQ-STR-003',
                Decimal('6850000000'),
                65,
                (
                    'Struktur utama selesai; fokus pada pool shell, '
                    'waterproofing, dan pekerjaan sipil luar.'
                ),
            ),
            (
                'Architecture',
                'NCV-BOQ-ARC-004',
                Decimal('4200000000'),
                57,
                (
                    'Mockup batu disetujui dan pemasangan screen kayu '
                    'dimulai pada Villa Wing A.'
                ),
            ),
            (
                'MEP & Landscape',
                'NCV-BOQ-MEP-002',
                Decimal('2950000000'),
                52,
                (
                    'Rough-in plumbing dan electrical berjalan paralel; '
                    'shop drawing landscape dalam koordinasi.'
                ),
            ),
        )
        boqs = []
        for index, (name, number, total, progress, notes) in enumerate(
            specs,
            start=1,
        ):
            boq = self._upsert(
                BillOfQuantity,
                {'project': project, 'document_name': name},
                {
                    'status': DocumentStatus.APPROVED,
                    'approval_required': True,
                    'approval_level': ApprovalLevel.LEVEL_2,
                    'issue_date': today - timedelta(days=130),
                    'due_date': today - timedelta(days=115),
                },
            )
            self._save_with_asset(
                BillOfQuantityVersion,
                {'boq': boq, 'document_number': number},
                {
                    'status': DocumentStatus.APPROVED,
                    'title': f'{name} — Approved Budget',
                    'total': Money(total, 'IDR'),
                    'notes': (
                        f'{DEMO_MARKER} Budget terkontrol untuk paket {name}.'
                    ),
                },
                'boq_file',
                'blueprint',
                f'{number.lower()}.jpg',
            )

            for week_number, percentage, report_date in (
                (23, max(progress - 6, 0), today - timedelta(days=14)),
                (24, progress, today - timedelta(days=7)),
            ):
                self._save_with_asset(
                    ProgressReport,
                    {
                        'boq_item': boq,
                        'progress_number': week_number,
                    },
                    {
                        'type': DurationType.WEEKS,
                        'report_date': report_date,
                        'progress_percentage': percentage,
                        'notes': notes,
                    },
                    'attachment',
                    'progress',
                    (
                        f'progress-{number.lower()}-'
                        f'week-{week_number}.jpg'
                    ),
                )
            boqs.append(boq)
        return boqs

    def _seed_schedules(self, boqs):
        today = timezone.localdate()
        specs = (
            (
                boqs[0],
                today - timedelta(days=150),
                today + timedelta(days=15),
                165,
                'Pool shell dan external civil ditargetkan selesai.',
            ),
            (
                boqs[1],
                today - timedelta(days=75),
                today + timedelta(days=70),
                145,
                'Finishing stone, teak screen, ceiling, dan joinery.',
            ),
            (
                boqs[2],
                today - timedelta(days=45),
                today + timedelta(days=100),
                145,
                'MEP rough-in, equipment, testing, dan landscape.',
            ),
        )
        for index, (boq, start, end, duration, notes) in enumerate(
            specs,
            start=1,
        ):
            self._save_with_asset(
                Schedule,
                {'boq_item': boq},
                {
                    'duration': duration,
                    'duration_in_field': duration - 5,
                    'duration_for_client': duration,
                    'duration_type': DurationType.DAYS,
                    'start_date': start,
                    'end_date': end,
                    'status': ScheduleStatusType.IN_PROGRESS,
                    'notes': notes,
                },
                'attachment',
                'blueprint',
                f'master-schedule-package-{index}.jpg',
            )

    def _seed_quality_records(self, project, references, profiles):
        now = timezone.now()
        open_defect = self._upsert(
            Defect,
            {
                'project': project,
                'work_title': 'Mockup nat batu courtyard',
            },
            {
                'location': 'Courtyard — Grid B3',
                'is_approved': False,
                'approved_at': now,
            },
        )
        self._save_with_asset(
            DefectDetail,
            {
                'deflect': open_defect,
                'location_detail': 'Dinding feature Villa Wing B',
            },
            {
                'deviation': (
                    'Lebar nat aktual 8–10 mm, target mockup 5 mm.'
                ),
                'initial_checklist_date': now - timedelta(days=5),
                'final_checklist_date': now + timedelta(days=3),
                'notes': (
                    'Bongkar area mockup 1,2 m² dan ulangi setelah '
                    'approval bersama architect.'
                ),
            },
            'photo',
            'progress',
            'defect-mockup-nat-batu.jpg',
        )

        closed_defect = self._upsert(
            Defect,
            {
                'project': project,
                'work_title': 'Leveling pool deck',
            },
            {
                'location': 'Main Pool — Grid C2',
                'is_approved': True,
                'approved_at': now - timedelta(days=9),
            },
        )
        self._save_with_asset(
            DefectDetail,
            {
                'deflect': closed_defect,
                'location_detail': 'Coping sisi timur main pool',
            },
            {
                'deviation': 'Selisih level 7 mm pada dua titik inspeksi.',
                'initial_checklist_date': now - timedelta(days=15),
                'final_checklist_date': now - timedelta(days=9),
                'notes': 'Rework selesai dan telah diverifikasi site manager.',
            },
            'photo',
            'progress',
            'closed-defect-pool-deck.jpg',
        )

        error_log = self._upsert(
            ErrorLog,
            {
                'project': project,
                'document_number': 'NCV-NCR-006',
            },
            {
                'work_type': references['work_structure'],
                'periode_start': now - timedelta(days=28),
                'periode_end': now - timedelta(days=25),
                'notes': (
                    'Perbaikan cover beton pada satu kolom service wing.'
                ),
            },
        )
        self._save_with_asset(
            ErrorLogDetail,
            {
                'error': error_log,
                'descriptions': 'Cover beton kurang pada Kolom SW-C04.',
            },
            {
                'date': timezone.localdate() - timedelta(days=28),
                'solutions': (
                    'Chipping terkontrol, treatment tulangan, dan repair '
                    'mortar sesuai method statement.'
                ),
                'person_in_charge': profiles['sm'],
                'open_date': timezone.localdate() - timedelta(days=28),
                'close_date': timezone.localdate() - timedelta(days=25),
                'status': ErrorLogStatus.RESOLVED,
            },
            'photo_proof',
            'progress',
            'ncr-column-repair.jpg',
        )

    def _seed_material_master(self, references):
        specs = (
            (
                'NCV-MAT-001',
                'Besi Tulangan D13',
                references['material_structural'],
                references['brand_krakatau'],
                references['unit_kg'],
                Decimal('14500'),
                Decimal('750'),
                'Besi ulir fy 420 untuk struktur utama dan pool.',
            ),
            (
                'NCV-MAT-002',
                'Semen Portland PCC',
                references['material_structural'],
                references['brand_tiga_roda'],
                references['unit_bag'],
                Decimal('72000'),
                Decimal('120'),
                'Semen PCC 40 kg untuk masonry dan pekerjaan sipil.',
            ),
            (
                'NCV-MAT-003',
                'Batu Vulkanik Bali',
                references['material_finishing'],
                references['brand_local'],
                references['unit_m2'],
                Decimal('315000'),
                Decimal('55'),
                'Batu seleksi warna charcoal untuk courtyard dan pool.',
            ),
            (
                'NCV-MAT-004',
                'Kayu Jati Outdoor',
                references['material_finishing'],
                references['brand_local'],
                references['unit_m3'],
                Decimal('16500000'),
                Decimal('4'),
                'Jati kiln-dried untuk screen facade dan pergola.',
            ),
        )
        materials = {}
        for (
            code,
            name,
            category,
            brand,
            unit,
            price,
            minimum_stock,
            descriptions,
        ) in specs:
            material = self._upsert(
                Material,
                {'code': code},
                {
                    'name': name,
                    'category': category,
                    'brand': brand,
                    'unit': unit,
                    'standart_price': Money(price, 'IDR'),
                    'minimum_stock': minimum_stock,
                    'descriptions': descriptions,
                },
            )
            materials[code] = material
        return materials

    def _seed_expenses_and_inventory(
        self,
        project,
        references,
        materials,
        profiles,
    ):
        today = timezone.localdate()
        expense = self._save_with_asset(
            ExpenseOnProject,
            {
                'project': project,
                'notes': (
                    f'{DEMO_MARKER} Procurement dan operasional site '
                    'periode minggu 24.'
                ),
            },
            {
                'date': today - timedelta(days=9),
            },
            'photo_proof',
            'progress',
            'expense-proof-week-24.jpg',
        )

        detail_specs = (
            (
                'Tenaga kerja sipil — minggu 24',
                references['expense_labor'],
                Decimal('1'),
                Decimal('285000000'),
                Decimal('0'),
                None,
                'Mandor, tukang, helper, dan lembur terverifikasi.',
            ),
            (
                'Sewa concrete pump dan scaffolding',
                references['expense_equipment'],
                Decimal('1'),
                Decimal('45000000'),
                Decimal('5'),
                DiscountType.PERCENTAGE,
                'Sewa alat periode empat minggu.',
            ),
        )
        for (
            name,
            category,
            quantity,
            unit_price,
            discount,
            discount_type,
            notes,
        ) in detail_specs:
            self._upsert(
                ExpenseDetail,
                {'expense': expense, 'name': name},
                {
                    'category': category,
                    'unit': references['unit_lump_sum'],
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount': discount,
                    'discount_type': discount_type,
                    'notes': notes,
                },
            )

        material_quantities = {
            'NCV-MAT-001': (Decimal('5200'), Decimal('14500')),
            'NCV-MAT-002': (Decimal('800'), Decimal('72000')),
            'NCV-MAT-003': (Decimal('420'), Decimal('315000')),
            'NCV-MAT-004': (Decimal('38'), Decimal('16500000')),
        }
        for code, (quantity, unit_price) in material_quantities.items():
            material = materials[code]
            self._upsert(
                ExpenseForMaterial,
                {'expense': expense, 'material': material},
                {
                    'category': references['expense_material'],
                    'unit': material.unit,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount': Decimal('0'),
                    'discount_type': None,
                },
            )

        quantity_used = {
            'NCV-MAT-001': Decimal('4380'),
            'NCV-MAT-002': Decimal('640'),
            'NCV-MAT-003': Decimal('286'),
            'NCV-MAT-004': Decimal('21'),
        }
        for code, used in quantity_used.items():
            material = materials[code]
            material_on_project = MaterialOnProject.objects.get(
                project=project,
                material=material,
            )
            material_on_project.quantity_used = used
            material_on_project.notes = (
                'Stock dan pemakaian terakhir dari laporan logistics '
                'minggu 24.'
            )
            material_on_project.approved_by = profiles['pm']
            material_on_project.approved_date = timezone.now()
            if (
                self.refresh_media
                or not material_on_project.photo
            ):
                material_on_project.photo = self._asset(
                    'progress',
                    f'material-{code.lower()}.jpg',
                )
            material_on_project.save()

        self._upsert(
            PurchaseRequest,
            {
                'project': project,
                'material': materials['NCV-MAT-003'],
                'notes': (
                    f'{DEMO_MARKER} Buffer batu seleksi untuk Wing C.'
                ),
            },
            {
                'quantity': Decimal('85'),
                'status': PurchaseRequestStatus.PENDING,
                'requested_by': profiles['logistic'],
                'approved_by': None,
                'approved_at': None,
                'ordered_at': None,
                'received_at': None,
            },
        )
        expense.recalculate_total()

    def _seed_tools(self, project, references):
        today = timezone.localdate()
        laser = self._upsert(
            Tool,
            {'serial_number': 'NCV-LASER-001'},
            {
                'category': references['tool_measuring'],
                'name': 'Rotary Laser Level',
                'conditions': 'Baik, kalibrasi aktif.',
                'amount': 3,
                'is_under_maintenance': False,
                'maintenance_interval_days': 90,
                'last_maintenance_date': today - timedelta(days=28),
                'next_maintenance_date': today + timedelta(days=62),
            },
        )
        vibrator = self._upsert(
            Tool,
            {'serial_number': 'NCV-VIB-002'},
            {
                'category': references['tool_power'],
                'name': 'Concrete Vibrator 1.5 kW',
                'conditions': 'Perlu penggantian bearing.',
                'amount': 4,
                'is_under_maintenance': False,
                'maintenance_interval_days': 60,
                'last_maintenance_date': today - timedelta(days=66),
                'next_maintenance_date': today - timedelta(days=6),
            },
        )
        self._upsert(
            ToolOnProject,
            {'project': project, 'tool': laser},
            {
                'amount': 2,
                'assigned_date': today - timedelta(days=120),
                'returned_date': None,
            },
        )
        self._upsert(
            ToolOnProject,
            {'project': project, 'tool': vibrator},
            {
                'amount': 2,
                'assigned_date': today - timedelta(days=90),
                'returned_date': None,
            },
        )
        self._upsert(
            ToolMaintenance,
            {
                'tool': vibrator,
                'scheduled_date': today + timedelta(days=2),
            },
            {
                'completed_date': None,
                'status': ToolMaintenanceStatus.SCHEDULED,
                'cost': Money(Decimal('1250000'), 'IDR'),
                'notes': (
                    f'{DEMO_MARKER} Preventive maintenance dan penggantian '
                    'bearing.'
                ),
            },
        )

    def _seed_finance(self, project, references):
        today = timezone.localdate()
        payment_request = self._save_with_asset(
            PaymentRequest,
            {
                'project': project,
                'payment_name': 'Progress Claim 02',
            },
            {
                'status': DocumentStatus.APPROVED,
                'approval_required': True,
                'approval_level': ApprovalLevel.LEVEL_2,
                'issue_date': today - timedelta(days=35),
                'due_date': today - timedelta(days=21),
            },
            'payment_proof',
            'hero',
            'progress-claim-02-proof.jpg',
        )
        self._save_with_asset(
            PaymentRequestVersion,
            {
                'payment_request': payment_request,
                'payment_number': 'NCV-CLM-002',
            },
            {
                'status': DocumentStatus.APPROVED,
                'title': 'Progress Claim 02 — Approved',
                'total': Money(Decimal('5400000000'), 'IDR'),
                'notes': (
                    f'{DEMO_MARKER} Termin berdasarkan progress tervalidasi.'
                ),
            },
            'payment_file',
            'blueprint',
            'progress-claim-02.jpg',
        )

        ledger_specs = (
            (
                'Client payment — Progress Claim 02',
                today - timedelta(days=20),
                Decimal('5400000000'),
                Decimal('0'),
            ),
            (
                'Site procurement — Week 24',
                today - timedelta(days=9),
                Decimal('0'),
                Decimal('1178100000'),
            ),
            (
                'Subcontractor stonework — Interim payment',
                today - timedelta(days=5),
                Decimal('0'),
                Decimal('325000000'),
            ),
        )
        for description, date, debit, credit in ledger_specs:
            self._upsert(
                FinanceData,
                {'project': project, 'description': description},
                {
                    'other': None,
                    'date': date,
                    'debet': Money(debit, 'IDR'),
                    'credit': Money(credit, 'IDR'),
                    'is_reconciled': True,
                    'reconciled_by': None,
                    'reconciled_at': timezone.now(),
                },
            )

        petty_specs = (
            (
                'Site induction dan air minum tim',
                today - timedelta(days=4),
                Decimal('3500000'),
            ),
            (
                'Consumable alat dan safety signage',
                today - timedelta(days=2),
                Decimal('4750000'),
            ),
        )
        for index, (description, date, credit) in enumerate(
            petty_specs,
            start=1,
        ):
            self._save_with_asset(
                PettyCash,
                {'project': project, 'description': description},
                {
                    'type': references['finance_project'],
                    'payment_via': references['payment_transfer'],
                    'other': None,
                    'date': date,
                    'debet': Money(Decimal('0'), 'IDR'),
                    'credit': Money(credit, 'IDR'),
                    'is_reconciled': False,
                    'reconciled_by': None,
                    'reconciled_at': None,
                },
                'photo_proof',
                'progress',
                f'petty-cash-proof-{index}.jpg',
            )

    def _seed_notifications(self, project, profiles):
        action_url = (
            f'/admin/project/project/{project.pk}/change/'
        )
        for key in ('pm', 'architect', 'sm', 'qs', 'logistic'):
            self._upsert(
                Notifications,
                {
                    'user': profiles[key],
                    'dedupe_key': f'demo-niskala-week-24-{key}',
                },
                {
                    'title': 'Koordinasi mingguan Niskala',
                    'message': (
                        'Progress minggu 24 telah diperbarui. Mohon review '
                        'look-ahead, material kritis, dan open defect.'
                    ),
                    'category': NotificationCategory.DEADLINE,
                    'action_url': action_url,
                    'is_read': key in {'pm', 'sm'},
                    'sent_at': timezone.now() - timedelta(days=1),
                },
            )

    def _seed_approvals(self, project, profiles):
        targets = (
            (
                Document.objects.get(
                    project=project,
                    document_name='Laporan Mingguan 24',
                ),
                profiles['pm'].user,
                'document',
                'pm,sm,ceo',
                'Mohon review laporan progres dan look-ahead minggu 24.',
            ),
            (
                Drawing.objects.get(
                    project=project,
                    document_name='Pool Detail',
                ),
                profiles['architect'].user,
                'drawing',
                'architect,pm,ceo',
                'Mohon approval detail pool sebelum pekerjaan lanjutan.',
            ),
            (
                PurchaseRequest.objects.get(
                    project=project,
                    material__code='NCV-MAT-003',
                ),
                profiles['logistic'].user,
                'purchase_request',
                'logistic,pm,cfo',
                'Permintaan buffer batu untuk menjaga produktivitas Wing C.',
            ),
        )
        for (
            target,
            requester,
            workflow_type,
            required_role,
            comment,
        ) in targets:
            content_type = ContentType.objects.get_for_model(
                target,
                for_concrete_model=False,
            )
            already_seeded = ApprovalRequest.all_objects.filter(
                content_type=content_type,
                object_id=str(target.pk),
            ).exists()
            if already_seeded:
                continue
            submit_for_approval(
                target,
                requester,
                workflow_type=workflow_type,
                required_role=required_role,
                comment=f'{DEMO_MARKER} {comment}',
            )
