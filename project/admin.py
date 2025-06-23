import nested_admin
from django.contrib import admin
from team.models import SubContractorOnProject
from finance.models import BillOfQuantity
from .models import *
from .forms import *
from rangefilter.filters import DateRangeFilter, NumericRangeFilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe


# ──────────────── Document & Versions ────────────────

class DocumentVersionInline(nested_admin.NestedTabularInline):
    model           = DocumentVersion
    extra           = 0
    fields          = ('title', 'document_number', 'document_file', 'status', 'notes', 'comment', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')

class SignatureOnDocumentInline(nested_admin.NestedTabularInline):
    model   = SignatureOnDocument
    extra   = 0
    fields  = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Document)
class DocumentAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('project', 'document_name', 'document_type', 'status', 'issue_date', 'due_date')
    list_filter   = ('project', 'document_type', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter), 'approval_required', 'approval_level')
    search_fields = ('project__project_name', 'document_name')
    fields        = ('project', 'document_name', 'document_type', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date')
    inlines       = [DocumentVersionInline,]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnDocumentInline(self.model, self.admin_site))

        return inline_instances
    
# ──────────────── Drawing & Versions ────────────────

class DrawingVersionInline(nested_admin.NestedTabularInline):
    model           = DrawingVersion
    extra           = 0
    fields          = ('title', 'document_number', 'drawing_file', 'status', 'notes', 'comment', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')

class SignatureOnDrawingInline(nested_admin.NestedTabularInline):
    model   = SignatureOnDrawing
    extra   = 0
    fields  = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Drawing)
class DrawingAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('project', 'document_name', 'drawing_type', 'status', 'issue_date', 'due_date')
    list_filter   = ('project', 'drawing_type', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter))
    search_fields = ('project__project_name', 'document_name')
    fields        = ('project', 'document_name', 'drawing_type', 'status', 'issue_date', 'due_date')
    inlines       = [DrawingVersionInline,]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnDrawingInline(self.model, self.admin_site))

        return inline_instances
    
# ──────────────── Deflect ────────────────

class DefectDetailInline(nested_admin.NestedTabularInline):
    model   = DefectDetail
    extra   = 0
    fields  = (
        'location_detail', 
        'deviation',
        'photo',
        'initial_checklist_date', 
        'initial_checklist_approval',
        'final_checklist_date',   
        'final_checklist_approval',
        'notes'
    )

class SignatureOnDeflectInline(nested_admin.NestedTabularInline):
    model = SignatureOnDeflect
    extra = 0
    fields = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Defect)
class DeflectAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('project', 'work_title', 'location', 'is_approved', 'approved_at')
    list_filter   = ('is_approved', 'project', ('approved_at', DateRangeFilter))
    search_fields = ('work_title',)
    fields        = ('project', 'work_title', 'location', 'is_approved', 'approved_at')
    inlines       = [DefectDetailInline, SignatureOnDeflectInline]

# ──────────────── ErrorLog & Details ────────────────

class ErrorLogDetailInline(nested_admin.NestedTabularInline):
    model   = ErrorLogDetail
    extra   = 0
    fields  = (
        'date', 
        'descriptions', 
        'solutions',
        'person_in_charge', 
        'open_date', 
        'close_date', 
        'photo_proof', 
        'status'
    )

class SignatureOnErrorLogInline(nested_admin.NestedTabularInline):
    model   = SignatureOnErrorLog
    extra   = 0
    fields  = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(ErrorLog)
class ErrorLogAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('project', 'work_type', 'periode_start', 'periode_end')
    list_filter   = ('work_type', 'project', ('periode_start', DateRangeFilter), ('periode_end', DateRangeFilter))
    search_fields = ('project__project_name', 'document_number', 'notes')
    fields        = ('project', 'document_number', 'work_type', 'periode_start', 'periode_end', 'notes')
    inlines       = [ErrorLogDetailInline, SignatureOnErrorLogInline]

# ──────────────── WorkMethod & Signatures ────────────────

class SignatureOnWorkMethodInline(nested_admin.NestedTabularInline):
    model = SignatureOnWorkMethod
    extra = 0
    fields = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(WorkMethod)
class WorkMethodAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('project', 'work_title', 'document_number', 'notes')
    list_filter   = ('project',)
    search_fields = ('work_title', 'document_number', 'notes')
    fields        = ('project', 'file', 'work_title', 'document_number', 'notes')
    inlines       = [SignatureOnWorkMethodInline]
    
    # def display_photo(self, obj):
    #     if obj.file:
    #         return format_html('<img src="{}" width="50" height="50" />'.format(obj.file.url))
    #     else:
    #         return mark_safe('<span>No Image</span>')
    # display_photo.short_description = 'Photo'

# ──────────────── Project ────────────────

class DocumentInline(nested_admin.NestedTabularInline):
    model           = Document
    extra           = 0
    fields          = ('document_name', 'document_type', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date')
    inlines         = [DocumentVersionInline, SignatureOnDocumentInline]

class DeflectInline(nested_admin.NestedTabularInline):
    model   = Defect
    extra   = 0
    fields  = ('work_title', 'location', 'is_approved', 'approved_at')
    inlines = [DefectDetailInline, SignatureOnDeflectInline]

class ErrorLogInline(nested_admin.NestedTabularInline):
    model   = ErrorLog
    extra   = 0
    fields  = ('document_number', 'work_type', 'periode_start', 'periode_end', 'notes')
    inlines = [ErrorLogDetailInline, SignatureOnErrorLogInline]

class WorkMethodInline(nested_admin.NestedTabularInline):
    model   = WorkMethod
    extra   = 0
    fields  = ('work_title', 'document_number', 'file', 'notes')
    inlines = [SignatureOnWorkMethodInline,]

class ProgressReportInline(nested_admin.NestedTabularInline):
    model           = ProgressReport
    extra           = 0
    fields          = ('boq_item', 'type', 'progress_number', 'report_date', 'progress_percentage', 'attachment', 'notes')

class ScheduleInline(nested_admin.NestedTabularInline):
    model           = Schedule
    extra           = 0
    fields          = ('boq_item', 'start_date', 'end_date', 'duration', 'duration_in_field', 'duration_for_client', 'duration_type', 'status', 'attachment', 'notes')

class BillOfQuantityInline(nested_admin.NestedTabularInline):
    model           = BillOfQuantity
    extra           = 0
    fields          = ('project', 'document_name', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')
    inlines         = [ScheduleInline, ProgressReportInline, ]

class SubContractorOnProjectInline(nested_admin.NestedTabularInline):
    model   = SubContractorOnProject
    extra   = 0
    fields  = ('subcon', 'is_active', 'descriptions')

@admin.register(Project)
class ProjectAdmin(nested_admin.NestedModelAdmin):
    list_display   = ('project_code', 'client', 'team', 'start_date', 'end_date', 'project_status', 'progress_with_percent')
    list_filter    = ('project_status', 'client', 'team', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter))
    search_fields  = ('project_code', 'project_name', 'client__user__username', 'team__name', 'description')
    date_hierarchy = 'start_date'
    fields         = ('project_code', 'project_name', 'location', 'client', 'team', 'start_date', 'end_date', 'project_status', 'progress', 'description')
    inlines        = [DocumentInline, DeflectInline, ErrorLogInline, WorkMethodInline, SubContractorOnProjectInline, BillOfQuantityInline]

    def progress_with_percent(self, obj):
        return f"{obj.progress} %"
    progress_with_percent.short_description = 'Progress'

# ──────────────── Schedule & WeeklyReport ────────────────

class SignatureOnScheduleInline(nested_admin.NestedTabularInline):
    model = SignatureOnSchedule
    extra = 0
    fields = ('signature', 'photo_proof')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if db_field.name == 'signature':
            # filter queryset agar hanya signature milik user yang login
            # asumsinya: Signature.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Signature.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Signature.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display  = ('boq_item', 'display_photo', 'start_date', 'end_date', 'duration', 'duration_type', 'status')
    list_filter   = ('duration_type', 'status', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter))
    search_fields = ('boq_item__description', 'notes')
    fields        = ('boq_item', 'start_date', 'end_date', 'duration', 'duration_in_field', 'duration_for_client', 'duration_type', 'status', 'attachment', 'notes')
    inlines       = [SignatureOnScheduleInline, ]

    def display_photo(self, obj):
        if obj.attachment:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.attachment.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'boq_item':
    #         kwargs["queryset"] = BillOfQuantityItemDetail.objects.select_related(
    #             'bill_of_quantity_subitem',
    #             'bill_of_quantity_subitem__bill_of_quantity_item',
    #         ).all()[:100]  # Limit jumlah data jika perlu
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display  = ('boq_item', 'display_photo', 'progress_number', 'type', 'report_date', 'progress_percentage')
    list_filter   = ('progress_number', 'type', ('report_date', DateRangeFilter), ('progress_percentage', NumericRangeFilter))
    search_fields = ('boq_item__description', 'notes')
    fields        = ('boq_item', 'type', 'progress_number', 'report_date', 'progress_percentage', 'attachment', 'notes')

    def display_photo(self, obj):
        if obj.attachment:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.attachment.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'boq_item':
    #         kwargs["queryset"] = BillOfQuantityItemDetail.objects.select_related(
    #             'bill_of_quantity_subitem',
    #             'bill_of_quantity_subitem__bill_of_quantity_item',
    #         ).all()[:100]  # Limit jumlah data jika perlu
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)