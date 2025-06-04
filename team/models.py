from django.utils import timezone
import os
import uuid
from django.db import models
from core.models import AuditModel, Location
from django_encrypted_filefield.fields import EncryptedImageField
from django.contrib.gis.db import models as gis_models
from django.conf import settings

class RoleType(models.TextChoices):
    ADMIN = "admin", "Admin"
    CEO = "ceo", "CEO"
    CTO = "cto", "CTO"
    CFO = "cfo", "CFO"
    QS = "qs", "QS"
    IT = "it", "IT"
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

class Profile(models.Model):
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
    profile_picture = models.ImageField(upload_to=upload_profile_picture, default='default_photo/default_profile.jpeg')
    is_active = models.BooleanField(default=True)
    update_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.full_name

# Create your models here.
class Team(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name

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
        return f'Signature {self.user.full_name}'

class Initial(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_initial')
    initial = EncryptedImageField()
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

class SubContractorWorker(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subcon = models.ForeignKey(SubContractor, on_delete=models.CASCADE, related_name='subcons_worker')
    worker_name = models.CharField(max_length=50)
    contact_number = models.CharField(max_length=20)

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
    date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    check_in_location = gis_models.PointField()
    check_out_location = gis_models.PointField()
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices)
    photo_check_in = models.ImageField(upload_to=upload_check_in)
    photo_check_out = models.ImageField(upload_to=upload_check_out)

    def __str__(self) -> str:
        return f'Attendance {self.user.full_name} on {self.date}'
    
class LeaveRequest (AuditModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='user_leave_request')
    status = models.CharField(max_length=20, choices=LeaveStatus.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    photo_proof = models.ImageField(upload_to=upload_leave_request, null=True, blank=True)
    approved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    approved_date = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f'Leave Request {self.user.full_name} from {self.start_date} to {self.end_date}'