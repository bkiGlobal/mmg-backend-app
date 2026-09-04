from django.utils import timezone
import os
import uuid
from django.db import models
from core.models import AuditModel, Location
from django_encrypted_filefield.fields import EncryptedImageField
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import datetime, time, timedelta

class RoleType(models.TextChoices):
    ADMIN = "admin", "Admin"
    CEO = "ceo", "CEO"
    CTO = "cto", "CTO"
    CFO = "cfo", "CFO"
    QS = "qs", "QS"
    IT = "it", "IT"
    PM = "pm", "PM"
    SALES = "sales", "Sales"
    SM = "sm", "SM"
    SPV = "spv", "Supervisor"
    ARCHITECT = "architect", "Architect"
    LOGISTIC = "logistic", "Logistic"
    PROJECT_ADMIN = "project_admin", "Project Admin"
    FINANCE_ADMIN = "finance_admin", "Finance Admin"
    WORKER = "worker", "Worker"
    CLIENT = "client", "Client"

class GenderType(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"

class StatusType(models.TextChoices):
    CONTRACT = "contract", "Contract"
    RESIGN = "resign", "Resign"
    PERMANENT = "permanent", "Permanent"
    PROBATION = "probation", "Probation"
    TERMINATED = "terminated", "Terminated"
    CLIENT = "client", "Client"

class AttendanceStatus(models.TextChoices):
    ONTIME = 'Ontime', 'Ontime'
    LATE = 'Late', 'Late'
    EARLY_LEAVE = 'Early Leave', 'Early Leave'
    LATE_EARLY_LEAVE = 'Late & Early Leave', 'Late & Early Leave'
    OVERTIME = 'Overtime', 'Overtime'
    ABSENT = 'Absent', 'Absent'
    LEAVE = 'Leave', 'Leave'
    HOLYDAY = 'Holiday', 'Holiday'


class AttendanceWorkMode(models.TextChoices):
    OFFICE = 'office', 'Office'
    WFH = 'wfh', 'Work From Home'


class LeaveStatus(models.TextChoices):
    PENDING = 'Pending', 'Pending'
    APPROVED = 'Approved', 'Approved'
    REJECTED = 'Rejected', 'Rejected'
    CANCELLED = 'Cancelled', 'Cancelled'


class NotificationCategory(models.TextChoices):
    GENERAL = 'general', 'General'
    APPROVAL = 'approval', 'Approval'
    DEADLINE = 'deadline', 'Deadline'
    INVENTORY = 'inventory', 'Inventory'
    ATTENDANCE = 'attendance', 'Attendance'
    SYSTEM = 'system', 'System'

def upload_signature(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'SGN_{timestamp_now}.jpeg'
    return os.path.join('signature_photo', filename)

def upload_initial(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'INT_{timestamp_now}.jpeg'
    return os.path.join('initial_photo', filename)

def upload_signature_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'SGP_{timestamp_now}.jpeg'
    return os.path.join('signature_proof_photo', filename)

def upload_profile_picture(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'PRP_{timestamp_now}.jpeg'
    return os.path.join('profile_photo', filename)

def upload_check_in(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'CKIN_{timestamp_now}.jpeg'
    return os.path.join('attendance', filename)

def upload_check_out(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'CKOT_{timestamp_now}.jpeg'
    return os.path.join('attendance', filename)

def upload_leave_request(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'LVR_{timestamp_now}.jpeg'
    return os.path.join('leave_request', filename)

def upload_id_worker(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'WKR_{timestamp_now}.jpeg'
    return os.path.join('id_worker', filename)


def default_signature_expiry():
    return timezone.now() + timedelta(days=30)


class WorkPolicy(AuditModel):
    name = models.CharField(max_length=100, unique=True)
    office_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_policies',
    )
    work_start = models.TimeField(default=time(9, 0))
    work_end = models.TimeField(default=time(17, 0))
    late_grace_minutes = models.PositiveIntegerField(default=15)
    overtime_after_minutes = models.PositiveIntegerField(default=30)
    geofence_radius_meters = models.PositiveIntegerField(default=100)
    allow_wfh = models.BooleanField(
        default=False,
        help_text='Izinkan staff memilih mode Work From Home.',
    )
    wfh_geofence_radius_meters = models.PositiveIntegerField(
        default=150,
        help_text=(
            'Radius maksimum dari alamat rumah pada profile ketika WFH.'
        ),
    )
    workdays = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Work policies'

    def clean(self):
        super().clean()
        errors = {}
        if self.work_start >= self.work_end:
            errors['work_end'] = (
                'Jam selesai kerja harus setelah jam mulai kerja.'
            )
        invalid_workdays = [
            day for day in self.workdays
            if not isinstance(day, int) or day < 0 or day > 6
        ]
        if invalid_workdays or len(set(self.workdays)) != len(self.workdays):
            errors['workdays'] = (
                'Workdays harus berisi angka unik 0 (Senin) sampai 6 (Minggu).'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.workdays:
            self.workdays = [0, 1, 2, 3, 4]
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class HolidaySource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    NATIONAL = 'national', 'Kalender Nasional'


class Holiday(AuditModel):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    source = models.CharField(
        max_length=20,
        choices=HolidaySource.choices,
        default=HolidaySource.MANUAL,
        help_text=(
            'Entri "Kalender Nasional" dibuat oleh sinkronisasi otomatis dan '
            'boleh ditimpa ulang. Entri manual tidak pernah diubah sync.'
        ),
    )

    class Meta:
        ordering = ('-date',)

    def __str__(self):
        return f'{self.name} ({self.date})'


class Profile(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=30, choices=RoleType.choices)
    gender = models.CharField(max_length=10, choices=GenderType.choices)
    status = models.CharField(max_length=20, choices=StatusType.choices)
    birthday = models.DateField()
    join_date = models.DateField()
    phone_number = models.CharField(max_length=20)
    profile_picture = models.ImageField(upload_to=upload_profile_picture, default='default_photo/default_profile.png')
    is_active = models.BooleanField(default=True)
    work_policy = models.ForeignKey(
        WorkPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    # update_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.full_name
    
class Team(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name
    
class TeamMember(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='team_members')
    is_active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('team', 'user'),
                condition=models.Q(is_deleted=False),
                name='team_unique_active_member',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.full_name} - {self.team.name}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
class Signature(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_signatures')
    signature = EncryptedImageField(upload_to=upload_signature)
    expire_at = models.DateTimeField(default=default_signature_expiry)

    def __str__(self) -> str:
        return f'Signature {self.user.full_name} expire at {self.expire_at.strftime("%a, %d %b %Y %H:%M:%S")}'

class Initial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_initial')
    initial = EncryptedImageField(upload_to=upload_initial)
    expire_at = models.DateTimeField(default=default_signature_expiry)

    def __str__(self) -> str:
        return f'Initial {self.user.full_name}'
    
class Notifications(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=NotificationCategory.choices,
        default=NotificationCategory.GENERAL,
    )
    action_url = models.CharField(max_length=500, blank=True)
    dedupe_key = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-sent_at',)
        indexes = [
            models.Index(
                fields=('user', 'is_read', '-sent_at'),
                name='team_notification_inbox_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'dedupe_key'),
                condition=~models.Q(dedupe_key=''),
                name='team_unique_notification_dedupe',
            ),
        ]

    def __str__(self):
        return f'{self.user}: {self.title}'

class SubContractor(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    locations = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    descriptions = models.TextField()
    contact_person = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name
    
class SubContractorWorker(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subcon = models.ForeignKey(SubContractor, on_delete=models.CASCADE, related_name='subcons_worker')
    worker_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=20)
    id_photo = models.ImageField(upload_to=upload_id_worker, null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.worker_name} from {self.subcon.name}'

class SubContractorOnProject(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('project.Project', on_delete=models.CASCADE, related_name='project_subcon')
    subcon = models.ForeignKey(SubContractor, on_delete=models.CASCADE, related_name='subcon_projects')
    is_active = models.BooleanField(default=True)
    descriptions = models.TextField()

    def __str__(self) -> str:
        return f'{self.subcon.name} in {self.project.project_name}'

class Attendance(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_attendance')
    date = models.DateField(default=timezone.localdate)
    check_in_location_label = models.CharField(max_length=108, null=True, blank=True)
    check_out_location_label = models.CharField(max_length=108, null=True, blank=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    check_in_location = gis_models.PointField(null=True, blank=True)
    check_out_location = gis_models.PointField(null=True, blank=True)
    check_in_accuracy_meters = models.FloatField(
        null=True,
        blank=True,
        editable=False,
    )
    check_out_accuracy_meters = models.FloatField(
        null=True,
        blank=True,
        editable=False,
    )
    check_in_distance_meters = models.FloatField(
        null=True,
        blank=True,
        editable=False,
    )
    check_out_distance_meters = models.FloatField(
        null=True,
        blank=True,
        editable=False,
    )
    work_mode = models.CharField(
        max_length=10,
        choices=AttendanceWorkMode.choices,
        default=AttendanceWorkMode.OFFICE,
    )
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices)
    status_override = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        null=True,
        blank=True,
        help_text=(
            'Khusus koreksi superuser. Jika diisi, nilai ini mengesampingkan '
            'status hasil perhitungan otomatis.'
        ),
    )
    status_override_reason = models.TextField(
        blank=True,
        help_text='Alasan koreksi status oleh superuser.',
    )
    photo_check_in = models.ImageField(
        upload_to=upload_check_in, null=True, blank=True
    )
    photo_check_out = models.ImageField(upload_to=upload_check_out, null=True, blank=True)
    work_policy = models.ForeignKey(
        WorkPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
    )
    worked_minutes = models.PositiveIntegerField(default=0, editable=False)
    overtime_minutes = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'date'),
                condition=models.Q(is_deleted=False),
                name='team_unique_active_attendance_day',
            ),
        ]

    def __str__(self) -> str:
        return f'Attendance {self.user.full_name} on {self.date}'
    
    def save(self, *args, **kwargs):
        self.set_attendance_status()
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if (
            self.status_override
            and not (self.status_override_reason or '').strip()
        ):
            raise ValidationError({
                'status_override_reason': (
                    'Alasan wajib diisi ketika status dioverride.'
                ),
            })

    def set_attendance_status(self):
        """
        Atur status absensi berdasarkan jam check in dan check out.
        Memperhatikan Timezone dan Null Safety.
        """
        
        # 1. Auto-fill waktu saat ini jika foto ada tapi waktu belum ada
        # Menggunakan timezone.now() agar sesuai settingan Django (USE_TZ)
        if not self.check_in and self.photo_check_in:
            self.check_in = timezone.now()
        
        if not self.check_out and self.photo_check_out:
            self.check_out = timezone.now()

        # 2. Guard Clause: record manual (leave/holiday/absent) dapat tidak
        # memiliki waktu check-in.
        if not self.check_in:
            if self.status_override:
                self.status = self.status_override
            return

        # 3. Konversi ke Local Time (SANGAT PENTING)
        # Database menyimpan UTC, kita harus ubah ke waktu lokal user (misal: WIB) sebelum ambil .time()
        local_check_in = timezone.localtime(self.check_in)
        local_check_out = timezone.localtime(self.check_out) if self.check_out else None

        # Ambil jam-nya saja
        jam_masuk = local_check_in.time()
        jam_keluar = local_check_out.time() if local_check_out else None

        policy = self.work_policy or self.user.work_policy
        if policy is None:
            policy = WorkPolicy.objects.filter(is_active=True).first()
        if policy and not self.work_policy_id:
            self.work_policy = policy

        attendance_date = self.date or local_check_in.date()
        if Holiday.objects.filter(date=attendance_date).exists():
            # Hari libur bukan hari kerja, sehingga tidak ada jam masuk yang
            # bisa dilanggar. Namun staff yang tetap bekerja harus terbayar:
            # seluruh durasi kerjanya dihitung sebagai lembur.
            self.worked_minutes = 0
            self.overtime_minutes = 0
            if local_check_out:
                worked = max(
                    int(
                        (local_check_out - local_check_in).total_seconds() // 60
                    ),
                    0,
                )
                self.worked_minutes = worked
                self.overtime_minutes = worked
            self.status = (
                self.status_override or AttendanceStatus.HOLYDAY
            )
            return

        # 4. Tentukan batas waktu berdasarkan kebijakan kerja.
        batas_masuk = policy.work_start if policy else time(9, 0)
        batas_keluar = policy.work_end if policy else time(17, 0)
        grace_minutes = policy.late_grace_minutes if policy else 0
        batas_masuk_dt = datetime.combine(
            attendance_date,
            batas_masuk,
            tzinfo=local_check_in.tzinfo,
        ) + timedelta(minutes=grace_minutes)

        # 5. Logic boolean biar lebih mudah dibaca (Refactoring)
        is_late = local_check_in > batas_masuk_dt
        
        # Jika belum check out, kita asumsikan TIDAK pulang cepat (masih kerja)
        is_early_leave = jam_keluar is not None and jam_keluar < batas_keluar

        self.worked_minutes = 0
        self.overtime_minutes = 0
        if local_check_out:
            worked = max(
                int((local_check_out - local_check_in).total_seconds() // 60),
                0,
            )
            self.worked_minutes = worked
            work_end_dt = datetime.combine(
                attendance_date,
                batas_keluar,
                tzinfo=local_check_out.tzinfo,
            )
            overtime_threshold = (
                policy.overtime_after_minutes if policy else 30
            )
            overtime = int(
                (local_check_out - work_end_dt).total_seconds() // 60
            )
            if overtime >= overtime_threshold:
                self.overtime_minutes = max(overtime, 0)

        # 6. Penentuan Status
        if is_late and is_early_leave:
            self.status = AttendanceStatus.LATE_EARLY_LEAVE
        elif is_late:
            self.status = AttendanceStatus.LATE
        elif is_early_leave:
            self.status = AttendanceStatus.EARLY_LEAVE
        elif self.overtime_minutes:
            self.status = AttendanceStatus.OVERTIME
        else:
            # Masuk tepat waktu DAN (pulang tepat waktu ATAU belum pulang)
            self.status = AttendanceStatus.ONTIME

        if self.status_override:
            self.status = self.status_override
    
class LeaveRequest (AuditModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_leave_request')
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_leave_request, null=True, blank=True)
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='team_leave_end_on_or_after_start',
            ),
        ]

    def __str__(self) -> str:
        return f'Leave Request {self.user.full_name} from {self.start_date} to {self.end_date}'

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {'end_date': 'End date tidak boleh sebelum start date.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
    
class SignatureOnLeaveRequest(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='leave_request_signatures')

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on BOQ {self.leave_request.user.full_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on BOQ {self.leave_request.user.full_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'
    
class Announcement(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=128)
    message = models.CharField(max_length=512)
