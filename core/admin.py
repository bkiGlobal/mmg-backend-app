from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.contrib.auth.models import Group, User
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.utils.html import format_html
from mapwidgets import GoogleMapPointFieldWidget
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import (
    AdminPasswordChangeForm as UnfoldAdminPasswordChangeForm,
    UserChangeForm as UnfoldUserChangeForm,
    UserCreationForm as UnfoldUserCreationForm,
)

from .admin_mixins import StatusBadgeAdminMixin
from .models import (
    ApprovalEvent,
    ApprovalRequest,
    ApprovalStatus,
    Brand,
    DataExportJob,
    DocumentType,
    ExpenseCategory,
    FinanceType,
    IncomeCategory,
    Location,
    MaterialCategory,
    PaymentVia,
    ToolCategory,
    UnitType,
    WorkType,
)
from .workflows import decide_approval


admin.site.site_header = 'MMG Construction Administration'
admin.site.site_title = 'MMG Admin'
admin.site.index_title = 'Operational Dashboard'
admin.site.site_url = 'https://mmg-construction.com/'


for model in (User, Group):
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass


class MMGUserChangeForm(UnfoldUserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        password = self.fields.get('password')
        if password:
            password.help_text = format_html(
                '<span class="mmg-password-help">'
                'Password mentah tidak disimpan dan tidak dapat ditampilkan.'
                '</span>'
                '<a class="mmg-password-change-button" '
                'href="../password/">'
                '<span class="material-symbols-outlined">lock_reset</span>'
                'Ubah password'
                '</a>'
            )


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = MMGUserChangeForm
    add_form = UnfoldUserCreationForm
    change_password_form = UnfoldAdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    list_display = (
        'action_time',
        'user',
        'content_type',
        'object_repr',
        'action_flag',
        'change_message',
    )
    list_filter = ('action_flag', 'user', 'content_type')
    search_fields = ('object_repr', 'change_message')
    date_hierarchy = 'action_time'
    ordering = ('-action_time',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Location)
class LocationsModelAdmin(ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)
    readonly_fields = ('latitude', 'longitude')
    formfield_overrides = {
        gis_models.PointField: {
            'widget': GoogleMapPointFieldWidget,
        },
    }


class LookupModelAdmin(ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


for model in (
    ExpenseCategory,
    IncomeCategory,
    DocumentType,
    WorkType,
    MaterialCategory,
    ToolCategory,
    UnitType,
    Brand,
    FinanceType,
    PaymentVia,
):
    admin.site.register(model, LookupModelAdmin)


class ApprovalEventInline(TabularInline):
    model = ApprovalEvent
    tab = True
    extra = 0
    can_delete = False
    fields = (
        'created_at',
        'actor',
        'from_status',
        'to_status',
        'comment',
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(StatusBadgeAdminMixin, ModelAdmin):
    list_before_template = 'admin/core/approval/pipeline.html'
    list_display = (
        'workflow_type',
        'target_display',
        'status',
        'required_role',
        'requested_by',
        'submitted_at',
        'decided_by',
    )
    list_filter = ('status', 'workflow_type', 'required_role')
    search_fields = (
        'workflow_type',
        'object_id',
        'requested_by__username',
        'comment',
    )
    readonly_fields = (
        'id',
        'content_type',
        'object_id',
        'target_display',
        'workflow_type',
        'status',
        'required_role',
        'requested_by',
        'submitted_at',
        'decided_by',
        'decided_at',
        'comment',
        'created_at',
        'created_by',
        'updated_at',
        'updated_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    inlines = (ApprovalEventInline,)
    actions = ('approve_selected', 'reject_selected')
    list_select_related = (
        'content_type',
        'requested_by',
        'decided_by',
    )

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        if not hasattr(response, 'context_data'):
            return response
        changelist = response.context_data.get('cl')
        if changelist is None:
            return response

        queryset = changelist.queryset
        status_counts = {
            row['status']: row['total']
            for row in queryset.values('status').annotate(
                total=Count('pk')
            )
        }
        stages = []
        stage_icons = {
            'pending': 'pending_actions',
            'approved': 'task_alt',
            'rejected': 'cancel',
            'cancelled': 'block',
        }
        for value, label in ApprovalStatus.choices:
            stages.append(
                {
                    'value': value,
                    'label': label,
                    'count': status_counts.get(value, 0),
                    'tone': self.get_status_tone(value),
                    'icon': stage_icons[value],
                }
            )

        workflows = list(
            queryset.values('workflow_type').annotate(
                total=Count('pk'),
                pending=Count(
                    'pk',
                    filter=Q(status=ApprovalStatus.PENDING),
                ),
                approved=Count(
                    'pk',
                    filter=Q(status=ApprovalStatus.APPROVED),
                ),
                rejected=Count(
                    'pk',
                    filter=Q(status=ApprovalStatus.REJECTED),
                ),
            ).order_by('-pending', '-total', 'workflow_type')[:6]
        )
        maximum = max(
            (workflow['total'] for workflow in workflows),
            default=1,
        )
        for workflow in workflows:
            workflow['width'] = (
                workflow['total'] / maximum * 100
                if maximum
                else 0
            )
            workflow['label'] = (
                workflow['workflow_type']
                .replace('_', ' ')
                .title()
            )

        response.context_data['approval_pipeline'] = {
            'stages': stages,
            'workflows': workflows,
            'total': queryset.count(),
        }
        return response

    @admin.display(description='Object')
    def target_display(self, obj):
        return str(obj.content_object) if obj.content_object else '-'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _decide(self, request, queryset, approve):
        success = 0
        for approval in queryset:
            try:
                decide_approval(
                    approval,
                    request.user,
                    approve=approve,
                    comment='Diproses melalui admin panel.',
                )
                success += 1
            except (ValidationError, PermissionDenied) as exc:
                self.message_user(
                    request,
                    f'{approval}: {exc}',
                    level=messages.ERROR,
                )
        self.message_user(
            request,
            f'{success} approval berhasil diproses.',
            level=messages.SUCCESS,
        )

    @admin.action(description='Approve approval terpilih')
    def approve_selected(self, request, queryset):
        self._decide(request, queryset, approve=True)

    @admin.action(description='Reject approval terpilih')
    def reject_selected(self, request, queryset):
        self._decide(request, queryset, approve=False)


@admin.register(ApprovalEvent)
class ApprovalEventAdmin(ModelAdmin):
    list_display = (
        'approval',
        'from_status',
        'to_status',
        'actor',
        'created_at',
    )
    list_filter = ('to_status', 'created_at')
    search_fields = (
        'approval__workflow_type',
        'approval__object_id',
        'actor__username',
        'comment',
    )
    readonly_fields = tuple(
        field.name for field in ApprovalEvent._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DataExportJob)
class DataExportJobAdmin(StatusBadgeAdminMixin, ModelAdmin):
    list_display = (
        'job_type',
        'status',
        'requested_by',
        'created_at',
        'completed_at',
        'download',
    )
    list_filter = ('status', 'job_type', 'created_at')
    search_fields = ('requested_by__username', 'error_message')
    readonly_fields = (
        'id',
        'job_type',
        'status',
        'requested_by',
        'parameters',
        'result_file',
        'row_count',
        'error_message',
        'started_at',
        'completed_at',
        'created_at',
        'created_by',
        'updated_at',
        'updated_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )
    actions = ('process_selected',)

    @admin.display(description='File')
    def download(self, obj):
        if obj.result_file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.result_file.url,
            )
        return '-'

    @admin.action(description='Proses export terpilih sekarang')
    def process_selected(self, request, queryset):
        from finance.export_jobs import process_export_job

        processed = 0
        for job in queryset:
            if job.status == 'failed':
                DataExportJob.all_objects.filter(pk=job.pk).update(
                    status='queued',
                    error_message='',
                    completed_at=None,
                )
                job.status = 'queued'
            if job.status == 'queued':
                process_export_job(job)
                processed += 1
        self.message_user(request, f'{processed} export diproses.')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
