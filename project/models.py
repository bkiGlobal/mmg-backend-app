from django.utils import timezone
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import models, router, transaction
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


def upload_project_presentation(instance, filename):
    _, ext = os.path.splitext(filename)
    timestamp_now = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f'PRJ_{timestamp_now}{ext}'
    return os.path.join('project_presentation', filename)


class Project(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_projects')
    project_name = models.CharField(max_length=255)
    project_code = models.CharField(max_length=255)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='team_project')
    description = models.TextField()
    presentation_image = models.ImageField(
        upload_to=upload_project_presentation,
        null=True,
        blank=True,
        help_text=(
            'Gambar hero/blueprint untuk showcase dan mode presentasi client.'
        ),
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        editable=False,
    )
    project_status = models.CharField(max_length=20, choices=ProjectStatus.choices, default=ProjectStatus.ON_GOING)

    class Meta:
        indexes = [
            models.Index(
                fields=('project_status', '-start_date', 'is_deleted'),
                name='project_admin_status_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress__gte=0, progress__lte=100),
                name='project_progress_between_0_100',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(end_date__isnull=True)
                    | models.Q(end_date__gte=models.F('start_date'))
                ),
                name='project_end_on_or_after_start',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.project_code} {self.project_name}'

    def clean(self):
        super().clean()
        errors = {}
        if self.progress is not None and not 0 <= self.progress <= 100:
            errors['progress'] = 'Progress harus berada antara 0 dan 100.'
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = 'End date tidak boleh sebelum start date.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def recalculate_progress(self, using=None):
        """Gunakan laporan terbaru setiap BOQ sebagai progress proyek."""
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        with transaction.atomic(using=database):
            locked = Project.all_objects.using(database).select_for_update().get(
                pk=self.pk
            )
            percentages = []
            for boq in locked.project_boqs.filter(is_deleted=False).only('pk'):
                latest = (
                    boq.reports_boq.filter(is_deleted=False)
                    .order_by('-report_date', '-progress_number', '-created_at')
                    .values_list('progress_percentage', flat=True)
                    .first()
                )
                if latest is not None:
                    percentages.append(Decimal(str(latest)))

            progress = (
                sum(percentages, Decimal('0')) / len(percentages)
                if percentages
                else Decimal('0')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            update_values = {'progress': progress}
            if locked.project_status not in {
                ProjectStatus.ON_HOLD,
                ProjectStatus.CANCELLED,
                ProjectStatus.TENDER,
            }:
                if progress >= Decimal('100'):
                    update_values['project_status'] = ProjectStatus.COMPLETED
                elif locked.end_date and locked.end_date < timezone.localdate():
                    update_values['project_status'] = ProjectStatus.DELAYED
                else:
                    update_values['project_status'] = ProjectStatus.ON_GOING

            Project.all_objects.using(database).filter(pk=self.pk).update(
                **update_values
            )
            self.progress = progress
            if 'project_status' in update_values:
                self.project_status = update_values['project_status']
        return progress

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

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'status', '-issue_date', 'is_deleted'),
                name='project_document_admin_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F('issue_date')),
                name='project_document_due_on_or_after_issue',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.document_name}'

    def clean(self):
        super().clean()
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValidationError(
                {'due_date': 'Due date tidak boleh sebelum issue date.'}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

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

    class Meta:
        indexes = [
            models.Index(
                fields=('project', 'status', '-issue_date', 'is_deleted'),
                name='project_drawing_admin_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F('issue_date')),
                name='project_drawing_due_on_or_after_issue',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.project.project_name} {self.document_name}'

    def clean(self):
        super().clean()
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValidationError(
                {'due_date': 'Due date tidak boleh sebelum issue date.'}
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)
        if self.status == DocumentStatus.APPROVED:
            from project.services import sync_approved_document

            sync_approved_document(self)
        return result

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
        result = super().save(*args, **kwargs)
        if (
            self.status == DocumentStatus.APPROVED
            and self.drawing.status == DocumentStatus.APPROVED
        ):
            from project.services import sync_approved_document

            sync_approved_document(self.drawing)
        return result

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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_defect')
    work_title = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField()

    def __str__(self) -> str:
        return f'Deflect {self.work_title} on {self.project.project_name}'
    
class DefectDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deflect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='defect_detail')
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
    deflect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='defect_signature')
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
    periode_end = models.DateTimeField(null=True, blank=True)
    notes = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(periode_end__isnull=True)
                    | models.Q(periode_end__gte=models.F('periode_start'))
                ),
                name='project_error_end_on_or_after_start',
            ),
        ]

    def __str__(self) -> str:
        return f'Error Log {self.work_type} on {self.project.project_name}'

    def clean(self):
        super().clean()
        if (
            self.periode_end
            and self.periode_start
            and self.periode_end < self.periode_start
        ):
            raise ValidationError(
                {
                    'periode_end': (
                        'Periode end tidak boleh sebelum periode start.'
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class ErrorLogDetail(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    error = models.ForeignKey(ErrorLog, on_delete=models.CASCADE, related_name='error_detail')
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
        return f'Error detail {self.error.work_type}: {self.descriptions[:50]}'

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration__gt=0),
                name='project_schedule_duration_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name='project_schedule_end_on_or_after_start',
            ),
        ]

    def __str__(self) -> str:
        try:
            return f'Schedule for {self.boq_item.document_name}'
        except Exception:
            return f'Schedule {self.pk}'

    def clean(self):
        super().clean()
        errors = {}
        if self.duration is None or self.duration <= 0:
            errors['duration'] = 'Duration harus lebih dari 0.'
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = 'End date tidak boleh sebelum start date.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if (
            self.end_date
            and self.end_date < timezone.localdate()
            and self.status not in {
                ScheduleStatusType.COMPLETED,
                ScheduleStatusType.CANCELLED,
                ScheduleStatusType.CANCELLED_BY_CLIENT,
                ScheduleStatusType.ON_HOLD,
            }
        ):
            self.status = ScheduleStatusType.OVERDUE
        self.full_clean()
        return super().save(*args, **kwargs)

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress_number__gt=0),
                name='project_report_number_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(
                    progress_percentage__gte=0,
                    progress_percentage__lte=100,
                ),
                name='project_report_progress_between_0_100',
            ),
        ]

    def __str__(self) -> str:
        try:
            return f'Report for {self.boq_item.document_name} in {self.type} {self.progress_number}'
        except Exception:
            return f'Schedule {self.pk}'

    def clean(self):
        super().clean()
        errors = {}
        if self.progress_number is None or self.progress_number <= 0:
            errors['progress_number'] = (
                'Progress number harus lebih dari 0.'
            )
        if (
            self.progress_percentage is None
            or not 0 <= self.progress_percentage <= 100
        ):
            errors['progress_percentage'] = (
                'Progress percentage harus berada antara 0 dan 100.'
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        database = kwargs.get('using') or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        kwargs['using'] = database
        affected_project_ids = {self.boq_item.project_id}
        if not self._state.adding:
            previous = ProgressReport.all_objects.using(database).get(pk=self.pk)
            affected_project_ids.add(previous.boq_item.project_id)
        self.full_clean()
        with transaction.atomic(using=database):
            result = super().save(*args, **kwargs)
            for project_id in affected_project_ids:
                Project.all_objects.using(database).get(
                    pk=project_id
                ).recalculate_progress(using=database)
        return result

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None
    ):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        project = self.boq_item.project
        with transaction.atomic(using=database):
            result = super().delete(
                using=database,
                keep_parents=keep_parents,
                user=user,
                cascade_at=cascade_at,
            )
            if result[0] and not project.is_deleted:
                project.recalculate_progress(using=database)
        return result

    def restore(self, using=None, user=None, cascade_at=None):
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        project = self.boq_item.project
        with transaction.atomic(using=database):
            result = super().restore(
                using=database,
                user=user,
                cascade_at=cascade_at,
            )
            if not project.is_deleted:
                project.recalculate_progress(using=database)
        return result

class WorkMethod(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='work_method_project')
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
