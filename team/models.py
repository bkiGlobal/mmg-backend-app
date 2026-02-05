from django.utils import timezone
import os
import uuid
from django.db import models
from core.models import AuditModel, Location
from django_encrypted_filefield.fields import EncryptedImageField
from django.contrib.gis.db import models as gis_models
from django.conf import settings
from datetime import time
from django_currentuser.middleware import get_current_authenticated_user

class RoleType(models.TextChoices):
    ADMIN = "admin", "Admin"
    CEO = "ceo", "CEO"
    CTO = "cto", "CTO"
    CFO = "cfo", "CFO"
    QS = "qs", "QS"
    IT = "it", "IT"
    PM = "pm", "PM"
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

class LeaveStatus(models.TextChoices):
    PENDING = 'Pending', 'Pending'
    APPROVED = 'Approved', 'Approved'
    REJECTED = 'Rejected', 'Rejected'
    CANCELLED = 'Cancelled', 'Cancelled'

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
    # update_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.full_name
    
    def delete(self, using=None, keep_parents=False):
        list_team_members = self.team_members.all()
        list_user_notifications = self.user_notifications.all()
        list_user_attendance = self.user_attendance.all()
        list_user_leave_request = self.user_leave_request.all()
        user = get_current_authenticated_user()
        for team in list_team_members:
            team.is_deleted  = True
            team.deleted_at  = timezone.now()
            if user:
                team.deleted_by = user
            team.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        for notification in list_user_notifications:
            notification.is_deleted  = True
            notification.deleted_at  = timezone.now()
            if user:
                notification.deleted_by = user
            notification.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        for attendance in list_user_attendance:
            attendance.is_deleted  = True
            attendance.deleted_at  = timezone.now()
            if user:
                attendance.deleted_by = user
            attendance.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        for leave_req in list_user_leave_request:
            leave_req.is_deleted  = True
            leave_req.deleted_at  = timezone.now()
            if user:
                leave_req.deleted_by = user
            leave_req.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        return super().delete(using, keep_parents)

class Team(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name
    
    def delete(self, using=None, keep_parents=False):
        list_members = self.members.all()
        user = get_current_authenticated_user()
        for member in list_members:
            member.is_deleted  = True
            member.deleted_at  = timezone.now()
            if user:
                member.deleted_by = user
            member.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        return super().delete(using, keep_parents)

class TeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='team_members')
    is_active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.full_name} - {self.team.name}"
    
class Signature(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_signatures')
    signature = EncryptedImageField(upload_to=upload_signature)
    expire_at = models.DateTimeField(auto_now_add=timezone.now() + timezone.timedelta(days=30))

    def __str__(self) -> str:
        return f'Signature {self.user.full_name} expire at {self.expire_at.strftime("%a, %d %b %Y %H:%M:%S")}'

class Initial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_initial')
    initial = EncryptedImageField(upload_to=upload_initial)
    expire_at = models.DateTimeField(auto_now_add=timezone.now() + timezone.timedelta(days=30))

    def __str__(self) -> str:
        return f'Initial {self.user.full_name}'
    
class Notifications(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField()
    sent_at = models.DateTimeField()

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
    
    def delete(self, using=None, keep_parents=False):
        list_workers = self.workers.all()
        list_subcontractors_on_project = self.subcontractors_on_project.all()
        user = get_current_authenticated_user()
        self.locations.is_deleted  = True
        self.locations.deleted_at  = timezone.now()
        if user:
            self.locations.deleted_by = user
        self.locations.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        for worker in list_workers:
            worker.is_deleted  = True
            worker.deleted_at  = timezone.now()
            if user:
                worker.deleted_by = user
            worker.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        for subcon_on_proj in list_subcontractors_on_project:
            subcon_on_proj.is_deleted  = True
            subcon_on_proj.deleted_at  = timezone.now()
            if user:
                subcon_on_proj.deleted_by = user
            subcon_on_proj.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        return super().delete(using, keep_parents)

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
    date = models.DateField(auto_now_add=True)
    check_in_location_label = models.CharField(max_length=108, null=True, blank=True)
    check_out_location_label = models.CharField(max_length=108, null=True, blank=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    check_in_location = gis_models.PointField(default='POINT(115.20762634277344 -8.639009475708008)')
    check_out_location = gis_models.PointField(default='POINT(115.20762634277344 -8.639009475708008)')
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices)
    photo_check_in = models.ImageField(upload_to=upload_check_in)
    photo_check_out = models.ImageField(upload_to=upload_check_out, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Attendance {self.user.full_name} on {self.date}'
    
    def save(self, *args, **kwargs):
        self.set_attendance_status()
        super().save(*args, **kwargs)
        
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

        # 2. Guard Clause: Jika check_in masih kosong, hentikan fungsi untuk mencegah error
        if not self.check_in:
            return 

        # 3. Konversi ke Local Time (SANGAT PENTING)
        # Database menyimpan UTC, kita harus ubah ke waktu lokal user (misal: WIB) sebelum ambil .time()
        local_check_in = timezone.localtime(self.check_in)
        local_check_out = timezone.localtime(self.check_out) if self.check_out else None

        # Ambil jam-nya saja
        jam_masuk = local_check_in.time()
        jam_keluar = local_check_out.time() if local_check_out else None

        # 4. Tentukan Batas Waktu
        batas_masuk = time(9, 0, 0)   # 09:00
        batas_keluar = time(17, 0, 0) # 17:00

        # 5. Logic boolean biar lebih mudah dibaca (Refactoring)
        is_late = jam_masuk > batas_masuk
        
        # Jika belum check out, kita asumsikan TIDAK pulang cepat (masih kerja)
        is_early_leave = jam_keluar is not None and jam_keluar < batas_keluar

        # 6. Penentuan Status
        if is_late and is_early_leave:
            self.status = AttendanceStatus.LATE_EARLY_LEAVE
        elif is_late:
            self.status = AttendanceStatus.LATE
        elif is_early_leave:
            self.status = AttendanceStatus.EARLY_LEAVE
        else:
            # Masuk tepat waktu DAN (pulang tepat waktu ATAU belum pulang)
            self.status = AttendanceStatus.ONTIME
    
class LeaveRequest (AuditModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_leave_request')
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_leave_request, null=True, blank=True)
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f'Leave Request {self.user.full_name} from {self.start_date} to {self.end_date}'
    
    def delete(self, using=None, keep_parents=False):
        list_leave_request_signatures = self.leave_request_signatures.all()
        user = get_current_authenticated_user()
        for leave_req in list_leave_request_signatures:
            leave_req.is_deleted  = True
            leave_req.deleted_at  = timezone.now()
            if user:
                leave_req.deleted_by = user
            leave_req.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
        return super().delete(using, keep_parents)
    
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