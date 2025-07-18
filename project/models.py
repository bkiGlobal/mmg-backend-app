from django.utils import timezone
import os
import uuid
from django.db import models
import magic
from core.models import *
from team.models import Team, Signature, Initial, upload_signature_proof, Profile

class ProjectStatus(models.TextChoices):
    ON_GOING = 'on_going', 'On Going'
    COMPLETED = 'completed', 'Completed'
    ON_HOLD = 'on_hold', 'On Hold'
    CANCELLED = 'cancelled', 'Cancelled'
    DELAYED = 'delayed', 'Delayed'
    TENDER = 'tender', 'Tender'

# class DocumentType(models.TextChoices):
#     PROJECT_PROPOSAL = 'project_proposal', 'Project Proposal'
#     FEASIBILITY_STUDY = 'feasibility_study', 'Feasibility Study'
#     DESIGN_BLUEPRINT = 'design_blueprint', 'Design Blueprint'
#     CONTRACT_AGREEMENT = 'contract_agreement', 'Contract Agreement'
#     SUBCONTRACT_AGREEMENT = 'subcontract_agreement', 'Subcontract Agreement'
#     PURCHASE_ORDER = 'purchase_order', 'Purchase Order'
#     PERMIT_APPLICATION = 'permit_application', 'Permit Application'
#     INSURANCE_DOCUMENT = 'insurance_document', 'Insurance Document'
#     DAILY_PROGRESS_REPORT = 'daily_progress_report', 'Daily Progress Report'
#     WEEKLY_PROGRESS_REPORT = 'weekly_progress_report', 'Weekly Progress Report'
#     MONTHLY_PROGRESS_REPORT = 'monthly_progress_report', 'Monthly Progress Report'
#     INSPECTION_REPORT = 'inspection_report', 'Inspection Report'
#     MEETING_MINUTES = 'meeting_minutes', 'Meeting Minutes'
#     PAYMENT_REQUEST = 'payment_request', 'Payment Request'
#     INVOICE = 'invoice', 'Invoice'
#     BUDGET_PLAN = 'budget_plan', 'Budget Plan'
#     MATERIAL_DELIVERY_ORDER = 'material_delivery_order', 'Material Delivery Order'
#     USAGE_REPORT = 'usage_report', 'Usage Report'
#     SAFETY_PLAN = 'safety_plan', 'Safety Plan'
#     ACCIDENT_REPORT = 'accident_report', 'Accident Report'
#     HANDOVER_CERTIFICATE = 'handover_certificate', 'Handover Certificate'
#     WARRANTY_DOCUMENT = 'warranty_document', 'Warranty Document'

class DocumentStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    IN_REVIEW = 'in_review', 'In Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    FINALIZED = 'finalized', 'Finalized'
    ARCHIVED = 'archived', 'Archived'
    DELETED = 'deleted', 'Deleted'

class ApprovalLevel(models.TextChoices):
    LEVEL_1 = 'level_1', 'Level 1'
    LEVEL_2 = 'level_2', 'Level 2'
    LEVEL_3 = 'level_3', 'Level 3'

# class WorkType(models.TextChoices):
#     FOUNDATION = "foundation", "Foundation"
#     STRUCTURE = "structure", "Structure"
#     FINISHING = "finishing", "Finishing"
#     ARCHITECTURE = "architecture", "Architecture"
#     MEP = "mep", "MEP"
#     OTHER = "other", "Other"

class ErrorLogStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    RESOLVED = "resolved", "Resolved"
    UNRESOLVED = "unresolved", "Unresolved"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    CANCELLED = "cancelled", "Cancelled"
    PENDING = "pending", "Pending"
    ESCALATED = "escalated", "Escalated"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    REOPENED = "reopened", "Reopened"
    DEFERRED = "deferred", "Deferred"
    RESOLVED_WITH_COMMENTS = "resolved_with_comments", "Resolved with Comments"

class ScheduleStatusType(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    DELAYED = "delayed", "Delayed"
    ON_HOLD = "on_hold", "On Hold"
    RESCHEDULED = "rescheduled", "Rescheduled"
    OVERDUE = "overdue", "Overdue"
    NOT_STARTED = "not_started", "Not Started"
    IN_REVIEW = "in_review", "In Review"
    AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED_BY_CLIENT = "cancelled_by_client", "Cancelled by Client"

class DurationType(models.TextChoices):
    DAYS = "days", "Days"
    WEEKS = "weeks", "Weeks"
    MONTHS = "months", "Months"
    YEARS = "years", "Years"

def upload_document(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    new_name = f"DCP_{timestamp_now}{ext}"
    return os.path.join('document_project', new_name)

def upload_drawing(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    new_name = f"DRW_{timestamp_now}{ext}"
    return os.path.join('drawing_project', new_name)

def upload_defect(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    new_name = f"DFT_{timestamp_now}{ext}"
    return os.path.join('defect_project', new_name)

def upload_error_proof(instance, filename):
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'ERR_{timestamp_now}.jpeg'
    return os.path.join('error_proof_photo', filename)

def upload_schedule_attachment(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'SCA_{timestamp_now}{ext}'
    return os.path.join('schedule_attachment_photo', filename)

def upload_weekly_report_attachment(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'PRA_{timestamp_now}{ext}'
    return os.path.join('weekly_report_attachment_photo', filename)

def upload_work_method_photo(instance, filename):
    base, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'WMT_{timestamp_now}{ext}'
    return os.path.join('work_method_photo', filename)

class Project(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_projects')
    project_name = models.CharField(max_length=255)
    project_code = models.CharField(max_length=255)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='team_project')
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    project_status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.ON_GOING)

    def __str__(self) -> str:
        return f'{self.project_code} {self.project_name}'

class Document(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_documents')
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    document_name = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    approval_required = models.BooleanField(default=True)
    approval_level = models.CharField(max_length=20, choices=ApprovalLevel.choices, null=True, blank=True)
    issue_date = models.DateField(verbose_name="Upload Date")
    due_date = models.DateField(verbose_name="Deadline Date")

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.document_name}'
    
    @property
    def project_name(self):
        return self.project.project_name

# def detect_mime(uploaded_file):
#     # Baca sebagian konten untuk identifikasi
#     mime = magic.from_buffer(uploaded_file.read(1024), mime=True)
#     uploaded_file.seek(0)  # Reset pointer
#     return mime

class DocumentVersion(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    title = models.CharField(max_length=255)
    document_file = models.FileField(upload_to=upload_document)
    document_number = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    notes = models.TextField()
    comment = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.document.document_name} {self.document_number}'

    def save(self, *args, **kwargs):
        # Jika file baru diupload
        # self.mime_type = detect_mime(self.file) 
        # if isinstance(self.file, UploadedFile):
        #     self.mime_type = self.file.content_type  # :contentReference[oaicite:3]{index=3}
        super().save(*args, **kwargs)

class SignatureOnDocument(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='document_signatures')

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on {self.document.document_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on {self.document.document_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'
    
class Drawing(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_drawings')
    drawing_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    document_name = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    issue_date = models.DateField(verbose_name="Upload Date")
    due_date = models.DateField(verbose_name="Deadline Date")

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.document_name}'
    
    def save(self, *args, **kwargs):
        if self.status == DocumentStatus.APPROVED:
            document,is_created = Document.objects.get_or_create(
                project=self.project,
                document_type=self.drawing_type,
                document_name=self.document_name,
                status=DocumentStatus.APPROVED,
                approval_required=True,
                approval_level=ApprovalLevel.LEVEL_1,
                issue_date=self.issue_date,
                due_date=self.due_date
            )
            version = DrawingVersion.objects.filter(
                drawing=self,
                status=DocumentStatus.APPROVED
            ).first()
            if is_created and version:
                DocumentVersion.objects.create(
                    document=document,
                    document_number=version.document_number,
                    document_file=version.drawing_file,
                    title=version.title,
                    status=DocumentStatus.APPROVED,
                    notes=version.notes
                )
            elif not is_created and version:
                # Update existing document version
                DocumentVersion.objects.filter(document=document).update(
                    document_number=version.document_number,
                    document_file=version.drawing_file,
                    title=version.title,
                    status=DocumentStatus.APPROVED,
                    notes=version.notes
                )
        return super().save(*args, **kwargs)

    @property
    def project_name(self):
        return self.project.project_name

class DrawingVersion(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drawing = models.ForeignKey(Drawing, on_delete=models.CASCADE, related_name='drawing_versions')
    title = models.CharField(max_length=255)
    drawing_file = models.FileField(upload_to=upload_drawing)
    document_number = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    notes = models.TextField()
    comment = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return f'{self.drawing.document_name} {self.document_number}'

    def save(self, *args, **kwargs):
        # Jika file baru diupload
        # self.mime_type = detect_mime(self.file) 
        # if isinstance(self.file, UploadedFile):
        #     self.mime_type = self.file.content_type  # :contentReference[oaicite:3]{index=3}
        super().save(*args, **kwargs)

class SignatureOnDrawing(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature = models.ForeignKey(Signature, on_delete=models.CASCADE)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)
    document = models.ForeignKey(Drawing, on_delete=models.CASCADE, related_name='drawing_signatures')

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on {self.document.document_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on {self.document.document_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'
    
class Defect(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_deflect')
    work_title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField()

    def __str__(self) -> str:
        return f'Deflect {self.work_title} on {self.project.project_name}'

class DefectDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deflect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='deflect_detail')
    location_detail = models.CharField(max_length=255)
    deviation = models.CharField(max_length=255)
    photo = models.ImageField(upload_to=upload_defect, null=True, blank=True)
    initial_checklist_date = models.DateTimeField()
    initial_checklist_approval = models.ForeignKey(Initial, on_delete=models.SET_NULL, null=True, blank=True, related_name='initial_approval')
    final_checklist_date = models.DateTimeField()
    final_checklist_approval = models.ForeignKey(Initial, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_approval')
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Deflect Detail {self.deflect.work_title} on {self.deflect.project.project_name}'

class SignatureOnDeflect(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deflect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='deflect_signature')
    signature = models.ForeignKey(Signature, on_delete=models.SET_NULL, null=True, blank=True)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on {self.deflect.work_title} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on {self.deflect.work_title} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'
    
class ErrorLog(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='error_on_project')
    work_type = models.ForeignKey(WorkType, on_delete=models.PROTECT)
    document_number = models.CharField(max_length=255)
    periode_start = models.DateTimeField()
    periode_end = models.DateTimeField()
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Error Log {self.work_type} on {self.project.project_name}'
    
class ErrorLogDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error = models.ForeignKey(ErrorLog, on_delete=models.CASCADE, related_name='error_dateil')
    date = models.DateField(default=timezone.now)
    descriptions = models.TextField()
    solutions = models.TextField()
    person_in_charge = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True)
    open_date = models.DateField()
    close_date = models.DateField()
    photo_proof = models.ImageField()
    status = models.CharField(max_length=50, choices=ErrorLogStatus.choices, default=ErrorLogStatus.OPEN)

    def __str__(self) -> str:
        return f'Error Log {self.date} on {self.descriptions}'

class SignatureOnErrorLog(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error = models.ForeignKey(ErrorLog, on_delete=models.CASCADE, related_name='error_log_signature')
    signature = models.ForeignKey(Signature, on_delete=models.SET_NULL, null=True, blank=True)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on Error {self.error.work_type} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on Error {self.error.work_type} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'

class Schedule(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boq_item = models.ForeignKey('finance.BillOfQuantity', on_delete=models.CASCADE, related_name='schedules_boq')
    duration = models.FloatField()
    duration_in_field = models.FloatField(null=True, blank=True)
    duration_for_client = models.FloatField(null=True, blank=True)
    duration_type = models.CharField(max_length=20, choices=DurationType.choices, default=DurationType.DAYS)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=ScheduleStatusType.choices, default=ScheduleStatusType.APPROVED)
    notes = models.TextField()
    attachment = models.FileField(upload_to=upload_schedule_attachment)

    def __str__(self) -> str:
        try:
            return f'Schedule for {self.boq_item.document_name}'
        except Exception:
            return f'Schedule {self.pk}'

class SignatureOnSchedule(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_signature')
    signature = models.ForeignKey(Signature, on_delete=models.SET_NULL, null=True, blank=True)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on Schedule {self.schedule.boq_item.document_name} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on Schedule {self.schedule.boq_item.document_name} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'
    
class ProgressReport(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    boq_item = models.ForeignKey('finance.BillOfQuantity', on_delete=models.CASCADE, related_name='reports_boq')
    type = models.CharField(max_length=25, choices=DurationType.choices, default=DurationType.WEEKS)
    progress_number = models.IntegerField()
    report_date = models.DateField()
    progress_percentage = models.FloatField()
    notes = models.TextField()
    attachment = models.FileField(upload_to=upload_weekly_report_attachment, null=True, blank=True)

    def __str__(self) -> str:
        try:
            return f'Report for {self.boq_item.document_name} in {self.type} {self.progress_number}'
        except Exception:
            return f'Schedule {self.pk}'

class WorkMethod(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    work_title = models.CharField(max_length=255)
    document_number = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_work_method_photo)
    notes = models.TextField()

    def __str__(self) -> str:
        return f'Work Method for {self.project.project_name}'

class SignatureOnWorkMethod(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_method = models.ForeignKey(WorkMethod, on_delete=models.CASCADE, related_name='work_method_signature')
    signature = models.ForeignKey(Signature, on_delete=models.SET_NULL, null=True, blank=True)
    photo_proof = models.ImageField(upload_to=upload_signature_proof)

    def __str__(self) -> str:
        if self.updated_at:
            return f'Signature {self.signature.user.full_name} on Work Method {self.work_method.document_number} at {self.updated_at.strftime("%d-%m-%Y %H:%M:%S")}'
        else:
            return f'Signature {self.signature.user.full_name} on Work Method {self.work_method.document_number} at {self.created_at.strftime("%d-%m-%Y %H:%M:%S")}'