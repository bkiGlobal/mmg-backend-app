from django.contrib import admin
from django.utils.html import format_html
from unfold.contrib.filters.admin import AutocompleteSelectFilter


class ProjectAutocompleteFilterAdminMixin:
    """Ubah filter relasi project menjadi pencarian autocomplete."""

    list_filter_submit = True

    def get_list_filter(self, request):
        filters = super().get_list_filter(request)
        enhanced_filters = []

        for configured_filter in filters:
            if (
                isinstance(configured_filter, str)
                and (
                    configured_filter == 'project'
                    or configured_filter.endswith('__project')
                )
            ):
                enhanced_filters.append(
                    (configured_filter, AutocompleteSelectFilter)
                )
            else:
                enhanced_filters.append(configured_filter)

        return tuple(enhanced_filters)


class StatusBadgeAdminMixin:
    """Render kolom ``status`` sebagai badge yang mudah dipindai."""

    status_success_values = {
        'active',
        'approved',
        'completed',
        'finalized',
        'ontime',
        'overtime',
        'present',
        'received',
        'resolved',
        'success',
    }
    status_warning_values = {
        'awaiting_approval',
        'in_progress',
        'in_review',
        'late',
        'late_and_early_leave',
        'early_leave',
        'on_hold',
        'ordered',
        'pending',
        'rescheduled',
    }
    status_danger_values = {
        'absent',
        'cancelled',
        'cancelled_by_client',
        'delayed',
        'inactive',
        'overdue',
        'rejected',
        'unresolved',
    }
    status_info_values = {
        'draft',
        'holiday',
        'leave',
        'not_started',
        'on_going',
        'open',
        'tender',
    }

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return tuple(
            'status_badge' if column == 'status' else column
            for column in list_display
        )

    def get_status_tone(self, value):
        normalized = (
            str(value or '')
            .strip()
            .lower()
            .replace('&', 'and')
            .replace(' ', '_')
        )
        if normalized in self.status_success_values:
            return 'success'
        if normalized in self.status_warning_values:
            return 'warning'
        if normalized in self.status_danger_values:
            return 'danger'
        if normalized in self.status_info_values:
            return 'info'
        return 'neutral'

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        value = str(getattr(obj, 'status', '') or '')
        label_method = getattr(obj, 'get_status_display', None)
        label = label_method() if callable(label_method) else value

        return format_html(
            '<span class="mmg-status-badge mmg-status-badge--{}">'
            '<span></span>{}</span>',
            self.get_status_tone(value),
            label or '-',
        )


class SoftDeleteAdminMixin(
    ProjectAutocompleteFilterAdminMixin,
    StatusBadgeAdminMixin,
):
    """Pastikan Django Admin memakai manager lengkap tanpa hard delete."""

    soft_delete_filter_parameter = 'is_deleted__exact'
    admin_select_related = ()
    list_per_page = 50
    show_full_result_count = False

    def get_queryset(self, request):
        queryset = self.model.all_objects.all()
        if self.admin_select_related:
            queryset = queryset.select_related(*self.admin_select_related)
        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)

        if self.soft_delete_filter_parameter in request.GET:
            return queryset
        return queryset.filter(is_deleted=False)

    def delete_model(self, request, obj):
        obj.delete(user=request.user)

    def delete_queryset(self, request, queryset):
        queryset.delete(user=request.user)

    def restore_queryset(self, request, queryset):
        return queryset.restore(user=request.user)

    def restore_selected(self, request, queryset):
        restored_count = self.restore_queryset(request, queryset)
        self.message_user(
            request,
            f"{restored_count} item berhasil di-restore.",
        )

    restore_selected.short_description = "Restore selected items"

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['restore_selected'] = (
            SoftDeleteAdminMixin.restore_selected,
            'restore_selected',
            SoftDeleteAdminMixin.restore_selected.short_description,
        )
        return actions


class ApprovalWorkflowAdminMixin:
    """Ajukan approval dari changelist dan kunci field keputusan."""

    approval_workflow_type = ''
    approval_required_role = 'admin'
    approval_readonly_fields = (
        'status',
        'approved_by',
        'approved_date',
        'approved_at',
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        field_names = {field.name for field in self.model._meta.fields}
        readonly.extend(
            field
            for field in self.approval_readonly_fields
            if field in field_names
        )
        return tuple(dict.fromkeys(readonly))

    def submit_for_approval_selected(self, request, queryset):
        from django.contrib import messages
        from django.core.exceptions import ValidationError

        from core.workflows import submit_for_approval

        submitted = 0
        for obj in queryset:
            try:
                submit_for_approval(
                    obj,
                    request.user,
                    workflow_type=self.approval_workflow_type,
                    required_role=self.approval_required_role,
                    comment='Diajukan melalui admin panel.',
                )
                submitted += 1
            except ValidationError as exc:
                self.message_user(
                    request,
                    f'{obj}: {exc}',
                    level=messages.ERROR,
                )
        self.message_user(
            request,
            f'{submitted} item masuk ke approval queue.',
            level=messages.SUCCESS,
        )

    submit_for_approval_selected.short_description = (
        'Ajukan item terpilih untuk approval'
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['submit_for_approval_selected'] = (
            ApprovalWorkflowAdminMixin.submit_for_approval_selected,
            'submit_for_approval_selected',
            ApprovalWorkflowAdminMixin.submit_for_approval_selected.short_description,
        )
        return actions
