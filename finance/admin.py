from decimal import Decimal

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Sum
from django.forms import formset_factory
from django.urls import path, reverse
from unfold.contrib.filters.admin import RangeDateFilter, RangeNumericFilter
from .models import *
from team.models import Profile
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .resources import *
from import_export.admin import ImportExportMixin
import pandas as pd
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from .forms import *
from .imports import import_expense_workbook
from .ledger_entries import save_ledger_spreadsheet
from core.admin_mixins import ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin
from core.models import DataExportJob, ExportJobStatus
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.import_export.forms import ExportForm, ImportForm


class LedgerBalanceAdminMixin:
    """Batch delete/restore ledger lalu hitung saldo sekali per kelompok."""

    def _recalculate_ledger_keys(self, keys, database):
        for project_id, other in keys:
            self.model.recalculate_ledger(
                project_id=project_id,
                other=other,
                using=database,
            )

    def delete_queryset(self, request, queryset):
        database = queryset.db
        with transaction.atomic(using=database):
            objects = list(queryset.select_for_update())
            keys = {obj.ledger_key for obj in objects}
            for obj in objects:
                obj.delete(
                    using=database,
                    user=request.user,
                    recalculate_balance=False,
                )
            self._recalculate_ledger_keys(keys, database)

    def restore_queryset(self, request, queryset):
        database = queryset.db
        restored_count = 0
        with transaction.atomic(using=database):
            objects = list(queryset.select_for_update())
            keys = {obj.ledger_key for obj in objects}
            for obj in objects:
                if obj.is_deleted:
                    obj.restore(
                        using=database,
                        user=request.user,
                        recalculate_balance=False,
                    )
                    restored_count += 1
            self._recalculate_ledger_keys(keys, database)
        return restored_count

    @admin.action(description='Tandai transaksi sudah direkonsiliasi')
    def reconcile_selected(self, request, queryset):
        count = queryset.update(
            is_reconciled=True,
            reconciled_by=request.user,
            reconciled_at=timezone.now(),
        )
        self.message_user(request, f'{count} transaksi direkonsiliasi.')

    @admin.action(description='Batalkan rekonsiliasi transaksi')
    def unreconcile_selected(self, request, queryset):
        count = queryset.update(
            is_reconciled=False,
            reconciled_by=None,
            reconciled_at=None,
        )
        self.message_user(request, f'{count} rekonsiliasi dibatalkan.')


class LedgerSpreadsheetAdminMixin:
    change_list_template = 'admin/finance/ledger_change_list.html'
    import_export_change_list_template = (
        'admin/finance/ledger_import_export_change_list.html'
    )
    spreadsheet_form_class = None
    spreadsheet_button_label = 'Spreadsheet'
    spreadsheet_title = 'Spreadsheet Input Mode'
    spreadsheet_description = (
        'Isi beberapa transaksi sekaligus. Seluruh baris akan disimpan '
        'secara atomik dan saldo dihitung ulang otomatis.'
    )

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    @property
    def spreadsheet_url_name(self):
        opts = self.model._meta
        return f'{opts.app_label}_{opts.model_name}_spreadsheet'

    def get_urls(self):
        custom_urls = [
            path(
                'spreadsheet/',
                self.admin_site.admin_view(self.spreadsheet_view),
                name=self.spreadsheet_url_name,
            ),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        extra_context = {
            **(extra_context or {}),
            'spreadsheet_url': reverse(
                f'admin:{self.spreadsheet_url_name}'
            ),
            'spreadsheet_button_label': self.spreadsheet_button_label,
        }
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        if hasattr(response, 'context_data'):
            changelist = response.context_data.get('cl')
            if changelist is not None:
                response.context_data['ledger_overview'] = (
                    self._build_ledger_overview(changelist.queryset)
                )
        return response

    @staticmethod
    def _amount(value):
        if hasattr(value, 'amount'):
            value = value.amount
        return Decimal(str(value or 0))

    @staticmethod
    def _format_idr(value):
        amount = LedgerSpreadsheetAdminMixin._amount(value)
        return f"Rp {amount:,.0f}".replace(',', '.')

    def _build_ledger_overview(self, queryset):
        totals = queryset.aggregate(
            debit=Sum('debet'),
            credit=Sum('credit'),
            transactions=Count('pk'),
        )
        debit = self._amount(totals['debit'])
        credit = self._amount(totals['credit'])
        grouped = list(
            queryset.values(
                'project_id',
                'project__project_code',
                'project__project_name',
                'other',
            ).annotate(
                debit_total=Sum('debet'),
                credit_total=Sum('credit'),
                transaction_count=Count('pk'),
            )
        )

        merged_groups = {}
        for group in grouped:
            group_debit = self._amount(group['debit_total'])
            group_credit = self._amount(group['credit_total'])
            if group['project_id']:
                group_key = ('project', group['project_id'])
                label = (
                    group['project__project_code']
                    or group['project__project_name']
                    or 'Project'
                )
                description = group['project__project_name'] or ''
            else:
                group_key = ('other', group['other'] or '')
                label = group['other'] or 'Ledger lainnya'
                description = 'Non-project'
            merged = merged_groups.setdefault(
                group_key,
                {
                    'label': label,
                    'description': description,
                    'debit_value': Decimal('0'),
                    'credit_value': Decimal('0'),
                    'transactions': 0,
                },
            )
            merged['debit_value'] += group_debit
            merged['credit_value'] += group_credit
            merged['transactions'] += group['transaction_count']

        rows = []
        for group in merged_groups.values():
            group_debit = group['debit_value']
            group_credit = group['credit_value']
            rows.append(
                {
                    'label': group['label'],
                    'description': group['description'],
                    'debit': self._format_idr(group_debit),
                    'credit': self._format_idr(group_credit),
                    'debit_value': group_debit,
                    'credit_value': group_credit,
                    'net': self._format_idr(group_debit - group_credit),
                    'transactions': group['transactions'],
                    'volume': group_debit + group_credit,
                }
            )

        rows.sort(key=lambda row: row['volume'], reverse=True)
        rows = rows[:6]
        maximum = max(
            (
                max(row['debit_value'], row['credit_value'])
                for row in rows
            ),
            default=Decimal('1'),
        ) or Decimal('1')
        for row in rows:
            row['debit_width'] = min(
                float(row['debit_value'] / maximum * 100),
                100,
            )
            row['credit_width'] = min(
                float(row['credit_value'] / maximum * 100),
                100,
            )

        return {
            'debit': self._format_idr(debit),
            'credit': self._format_idr(credit),
            'net': self._format_idr(debit - credit),
            'transactions': totals['transactions'] or 0,
            'unreconciled': queryset.filter(
                is_reconciled=False
            ).count(),
            'groups': rows,
        }

    def get_spreadsheet_formset_class(self):
        return formset_factory(
            self.spreadsheet_form_class,
            formset=LedgerSpreadsheetFormSet,
            extra=8,
            can_delete=True,
            max_num=50,
            validate_max=True,
        )

    def spreadsheet_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        formset_class = self.get_spreadsheet_formset_class()
        if request.method == 'POST':
            formset = formset_class(
                request.POST,
                request.FILES,
                prefix='rows',
            )
            if formset.is_valid():
                try:
                    created = save_ledger_spreadsheet(
                        self.model,
                        formset,
                        request.user,
                    )
                except ValidationError as exc:
                    formset._non_form_errors = formset.error_class(
                        exc.messages
                    )
                else:
                    self.message_user(
                        request,
                        (
                            f'{len(created)} transaksi berhasil disimpan. '
                            'Saldo ledger sudah dihitung ulang.'
                        ),
                        level=messages.SUCCESS,
                    )
                    return redirect(
                        reverse(
                            f'admin:{self.model._meta.app_label}_'
                            f'{self.model._meta.model_name}_changelist'
                        )
                    )
        else:
            formset = formset_class(prefix='rows')

        changelist_url = reverse(
            f'admin:{self.model._meta.app_label}_'
            f'{self.model._meta.model_name}_changelist'
        )
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': self.spreadsheet_title,
            'subtitle': None,
            'formset': formset,
            'changelist_url': changelist_url,
            'spreadsheet_description': self.spreadsheet_description,
            'proof_required': self.model is PettyCash,
        }
        return render(
            request,
            'admin/finance/ledger_spreadsheet.html',
            context,
        )

# class ScheduleInline(TabularInline):
#     model   = Schedule
#     extra   = 0
#     fields  = (
#         'boq_item', 
#         'start_date', 
#         'end_date', 
#         'duration', 
#         'duration_in_field', 
#         'duration_for_client', 
#         'duration_type', 
#         'status', 
#         'attachment', 
#         'notes'
#     )

# class BillOfQuantityItemDetailInline(TabularInline):
#     model   = BillOfQuantityItemDetail
#     inlines = [ScheduleInline]
#     extra   = 0
#     fields  = (
#         'item_number',
#         'description',
#         'quantity',
#         'unit_type',
#         'unit_price',
#         'total_price',
#         'work_weight',
#         'notes',
#     )
#     readonly_fields = ('total_price',)

# class BillOfQuantitySubItemInline(TabularInline):
#     model   = BillOfQuantitySubItem
#     inlines = [BillOfQuantityItemDetailInline]
#     extra   = 0
#     fields  = ('item_order', 'title', 'notes',)
#     readonly_fields = ('total_price',)

# class BillOfQuantityItemInline(TabularInline):
#     model   = BillOfQuantityItem
#     inlines = [BillOfQuantitySubItemInline]
#     extra   = 0
#     fields  = ('item_number', 'title', 'notes')
#     show_change_link = True

class SignatureOnBillOfQuantityInline(TabularInline):
    tab = True
    model   = SignatureOnBillOfQuantity
    extra   = 0
    classes = ['collapse']
    fields  = ('signature', ('photo_proof', 'display_photo'))
    readonly_fields = ('display_photo',)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        class FormSetWithControl(FormSet):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)

                try:
                    current_profile = request.user.profile
                except Profile.DoesNotExist:
                    current_profile = None

                for form in self.forms:
                    inst = form.instance
                    # Pastikan ini baris existing dan sudah punya FK signature
                    if inst.pk and inst.signature_id:
                        # kalau signature bukan punya user sekarang
                        if not current_profile or inst.signature.user_id != current_profile.id:
                            # disable kedua field
                            form.fields['signature'].disabled   = True
                            form.fields['photo_proof'].disabled = True
                            # supaya pilihan dropdown valid, batasi hanya ke pk ini
                            form.fields['signature'].queryset = Signature.objects.filter(
                                pk=inst.signature_id
                            )
        return FormSetWithControl

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

class BillOfQuantityVersionInline(TabularInline):
    tab = True
    model           = BillOfQuantityVersion
    extra           = 0
    classes         = ['collapse']
    fields          = ('title', 'document_number', 'boq_file', 'status', 'total', 'notes')
    readonly_fields = ('status',)

@admin.register(BillOfQuantity)
class BillOfQuantityAdmin(
    ApprovalWorkflowAdminMixin,
    SoftDeleteAdminMixin,
    ImportExportMixin,
    ModelAdmin,
):
    approval_workflow_type = 'bill_of_quantity'
    approval_required_role = 'qs,cfo,ceo'
    import_form_class = ImportForm
    export_form_class = ExportForm
    admin_select_related = ('project',)
    autocomplete_fields = ('project',)
    list_display    = ('project', 'document_name', 'status', 'issue_date', 'due_date', 'is_deleted')
    list_filter     = ('project', 'status', ('issue_date', RangeDateFilter), ('due_date', RangeDateFilter), 'approval_required', 'approval_level', 'is_deleted')
    search_fields   = ('project__project_name', 'document_name')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'document_name', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    inlines         = [BillOfQuantityVersionInline, ]  # hanya masukkan default di sini

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnBillOfQuantityInline(self.model, self.admin_site))

        return inline_instances
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected bill of quantitys")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for version in obj.boq_versions.all():
                if version.is_deleted:
                    version.is_deleted = False
                    version.deleted_at = None
                    version.deleted_by = None
                    version.save()
            for signature in obj.boq_signatures.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

class SignatureOnPaymentRequestInline(TabularInline):
    tab = True
    model   = SignatureOnPaymentRequest
    extra   = 0
    classes = ['collapse',]
    fields  = ('signature', ('photo_proof', 'display_photo'))
    readonly_fields = ('display_photo',)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def get_formset(self, request, obj=None, **kwargs):
        FormSet = super().get_formset(request, obj, **kwargs)
        class FormSetWithControl(FormSet):
            def __init__(self, *args, **inner_kwargs):
                super().__init__(*args, **inner_kwargs)

                try:
                    current_profile = request.user.profile
                except Profile.DoesNotExist:
                    current_profile = None

                for form in self.forms:
                    inst = form.instance
                    # Pastikan ini baris existing dan sudah punya FK signature
                    if inst.pk and inst.signature_id:
                        # kalau signature bukan punya user sekarang
                        if not current_profile or inst.signature.user_id != current_profile.id:
                            # disable kedua field
                            form.fields['signature'].disabled   = True
                            form.fields['photo_proof'].disabled = True
                            # supaya pilihan dropdown valid, batasi hanya ke pk ini
                            form.fields['signature'].queryset = Signature.objects.filter(
                                pk=inst.signature_id
                            )
        return FormSetWithControl
    
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

class PaymentRequestVersionInline(TabularInline):
    tab = True
    model           = PaymentRequestVersion
    extra           = 0
    classes         = ['collapse',]
    fields          = ('title', 'payment_number', 'payment_file', 'status', 'total', 'notes')
    readonly_fields = ('status',)

@admin.register(PaymentRequest)
class PaymentRequestAdmin(
    ApprovalWorkflowAdminMixin,
    SoftDeleteAdminMixin,
    ImportExportMixin,
    ModelAdmin,
):
    approval_workflow_type = 'payment_request'
    approval_required_role = 'cfo,ceo'
    import_form_class = ImportForm
    export_form_class = ExportForm
    admin_select_related = ('project',)
    autocomplete_fields = ('project',)
    list_display    = ('project', 'payment_name', 'status', 'issue_date', 'due_date', 'is_deleted')
    list_filter     = ('project', 'status', ('issue_date', RangeDateFilter), ('due_date', RangeDateFilter), 'approval_required', 'approval_level', 'is_deleted')
    search_fields   = ('project__project_name', 'payment_name')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'payment_name', 'status', 'payment_proof', 'approval_required', 'approval_level', 'issue_date', 'due_date'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    inlines         = [PaymentRequestVersionInline, ]  # hanya masukkan default di sini

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnPaymentRequestInline(self.model, self.admin_site))

        return inline_instances
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected payment requests")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for version in obj.payment_versions.all():
                if version.is_deleted:
                    version.is_deleted = False
                    version.deleted_at = None
                    version.deleted_by = None
                    version.save()
            for signature in obj.payment_request_signatures.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

#
# Inlines for Expense → ExpenseDetail & ExpenseForMaterial
#

class ExpenseDetailInline(TabularInline):
    tab = True
    model   = ExpenseDetail
    extra   = 0
    classes = ['collapse',]
    fields  = (
        'category',
        'name',
        'quantity',
        'unit',
        'unit_price',
        'subtotal',
        'discount',
        'discount_type',
        'discount_amount',
        'total',
        'notes',
    )
    readonly_fields = ('subtotal', 'discount_amount', 'total')

class ExpenseForMaterialInline(TabularInline):
    tab = True
    model   = ExpenseForMaterial
    extra   = 0
    classes = ['collapse',]
    fields  = (
        'material',
        'category',
        'quantity',
        'unit',
        'unit_price',
        'subtotal',
        'discount',
        'discount_type',
        'discount_amount',
        'total',
    )
    readonly_fields = ('subtotal', 'discount_amount', 'total')

@admin.register(ExpenseOnProject)
class ExpenseOnProjectAdmin(
    SoftDeleteAdminMixin, ModelAdmin
):
    admin_select_related = ('project',)
    autocomplete_fields = ('project',)
    list_display    = ('project', 'display_photo_view', 'date', 'total', 'is_deleted')
    list_filter     = ('project', ('date', RangeDateFilter), ('total', RangeNumericFilter), 'is_deleted')
    search_fields   = ('project__project_name', 'notes')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', ('photo_proof', 'display_photo'), 'date', 'total', 'notes'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('display_photo', 'total', 'created_by', 'created_at', 'updated_by', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by')
    resource_class = ExpenseResource
    inlines         = [ExpenseDetailInline, ExpenseForMaterialInline]
    change_list_template = "admin/expense_change_list.html"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)

    def save_formset(self, request, form, formset, change):
        if formset.model not in (ExpenseDetail, ExpenseForMaterial):
            return super().save_formset(
                request, form, formset, change
            )

        database = form.instance._state.db
        with transaction.atomic(using=database):
            instances = formset.save(commit=False)

            for deleted_object in formset.deleted_objects:
                deleted_object.delete(
                    user=request.user,
                    recalculate=False,
                )

            for instance in instances:
                instance.save(recalculate=False)

            formset.save_m2m()
            form.instance.recalculate_total(using=database)
    
    @admin.action(description="Restore selected expenses")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for detail in obj.expense_detail.all():
                if detail.is_deleted:
                    detail.is_deleted = False
                    detail.deleted_at = None
                    detail.deleted_by = None
                    detail.save()
            for material in obj.expense_material.all():
                if material.is_deleted:
                    material.is_deleted = False
                    material.deleted_at = None
                    material.deleted_by = None
                    material.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('export-all/', self.admin_site.admin_view(self.export_all), name='expense-export-all'),
            path('import-all/', self.admin_site.admin_view(self.import_all_view), name='finance_expense_import_all',),
        ]
        return custom + urls
    
    def export_all(self, request):
        from finance.export_jobs import enqueue_export

        job = enqueue_export('expense', requested_by=request.user)
        if job.status == ExportJobStatus.COMPLETED:
            message = 'Export selesai. File siap diunduh di halaman ini.'
            level = messages.SUCCESS
        elif job.status == ExportJobStatus.FAILED:
            message = f'Export gagal: {job.error_message}'
            level = messages.ERROR
        else:
            message = (
                'Export dimasukkan ke antrean. Jalankan '
                '`python manage.py process_export_jobs` atau scheduler '
                'untuk memprosesnya.'
            )
            level = messages.WARNING
        self.message_user(request, message, level=level)
        return redirect(
            f'/admin/core/dataexportjob/{job.pk}/change/'
        )
    
    def import_all_view(self, request):
        if request.method == 'POST':
            form = MultiSheetImportForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = form.cleaned_data['file']
                try:
                    xls = pd.ExcelFile(excel_file)
                    df_exp = xls.parse('Expense')
                    df_det = xls.parse('ExpenseDetail')
                    df_mat = xls.parse('ExpenseForMaterial')
                    with transaction.atomic():
                        counts = import_expense_workbook(
                            df_exp, df_det, df_mat
                        )
                        if form.cleaned_data['dry_run']:
                            transaction.set_rollback(True)
                except Exception as e:
                    self.message_user(
                        request,
                        f'Import dibatalkan: {e}',
                        level=messages.ERROR,
                    )
                    return render(
                        request,
                        'admin/import_all_expense.html',
                        {
                            **self.admin_site.each_context(request),
                            'form': form,
                            'title': 'Import Expense dari Excel',
                            'opts': self.model._meta,
                        },
                    )
                mode = (
                    'Validasi berhasil, tidak ada data yang disimpan'
                    if form.cleaned_data['dry_run']
                    else 'Import berhasil'
                )
                self.message_user(
                    request,
                    (
                        f"{mode}. Expense: +{counts['expense_created']} / "
                        f"~{counts['expense_updated']}; detail: "
                        f"+{counts['detail_created']} / "
                        f"~{counts['detail_updated']}; material: "
                        f"+{counts['material_created']} / "
                        f"~{counts['material_updated']}."
                    ),
                    level=messages.SUCCESS,
                )
                if not form.cleaned_data['dry_run']:
                    return redirect('..')
                return render(
                    request,
                    'admin/import_all_expense.html',
                    {
                        **self.admin_site.each_context(request),
                        'form': MultiSheetImportForm(
                            initial={'dry_run': False}
                        ),
                        'title': 'Import Expense dari Excel',
                        'preview_counts': counts,
                        'opts': self.model._meta,
                    },
                )
        else:
            form = MultiSheetImportForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Import Expense dari Excel',
            'opts': self.model._meta,
        }
        return render(request, 'admin/import_all_expense.html', context)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo_proof:
            return format_html(
                (
                    '<a href="{}" target="_blank" rel="noopener">'
                    '<img src="{}" alt="Bukti expense" loading="lazy" '
                    'style="width: 48px; height: 48px; object-fit: cover; '
                    'border-radius: 8px;" /></a>'
                ),
                obj.photo_proof.url,
                obj.photo_proof.url,
            )
        else:
            return "Tidak ada foto"
    display_photo_view.short_description = 'Foto'

#
# Inlines for Income → IncomeDetail
#
# class IncomeDetailInline(TabularInline):
#     model   = IncomeDetail
#     extra   = 0
#     fields  = (
#         'name',
#         'quantity',
#         'unit',
#         'unit_price',
#         'subtotal',
#         'discount',
#         'discount_type',
#         'discount_amount',
#         'total',
#         'notes',
#     )
#     readonly_fields = ('subtotal', 'total')

# @admin.register(Income)
# class IncomeAdmin(ModelAdmin):
#     list_display    = ('project', 'display_photo', 'received_from', 'payment_date', 'category', 'total')
#     list_filter     = ('project', 'category', ('payment_date', RangeDateFilter), ('total', RangeNumericFilter))
#     search_fields   = ('received_from', 'notes')
#     fields          = ('project', 'payment_proof', 'received_from', 'category', 'payment_date', 'total', 'notes')
#     readonly_fields = ('total',)
#     inlines         = [IncomeDetailInline]
#     change_list_template = "admin/income_change_list.html"

#     def get_urls(self):
#         from django.urls import path
#         urls = super().get_urls()
#         custom = [
#             path('export-all/', self.admin_site.admin_view(self.export_all), name='income-export-all'),
#             path('import-all/', self.admin_site.admin_view(self.import_all_view), name='finance_income_import_all',),
#         ]
#         return custom + urls

#     def export_all(self, request):
#         # 1) export kedua dataset
#         income_ds = IncomeResource().export()
#         detail_ds = IncomeDetailResource().export()

#         # 2) ubah ke DataFrame pandas
#         df_inc = pd.DataFrame(income_ds.dict)
#         df_det = pd.DataFrame(detail_ds.dict)

#         # 3) tulis ke Excel multi-sheet
#         buffer = io.BytesIO()
#         with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#             df_inc.to_excel(writer, sheet_name='Income', index=False)
#             df_det.to_excel(writer, sheet_name='IncomeDetail', index=False)
#         buffer.seek(0)

#         # 4) kembalikan HttpResponse sebagai file download
#         response = HttpResponse(
#             buffer,
#             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#         response['Content-Disposition'] = 'attachment; filename="income_full_export.xlsx"'
#         return response

#     def import_all_view(self, request):
#         """
#         Custom admin view untuk upload dan import file multi‐sheet Excel.
#         """
#         if request.method == 'POST':
#             form = MultiSheetImportForm(request.POST, request.FILES)
#             if form.is_valid():
#                 excel_file = form.cleaned_data['file']
#                 try:
#                     # Baca kedua sheet
#                     xls = pd.ExcelFile(excel_file)
#                     df_inc = xls.parse('Income')
#                     df_det = xls.parse('IncomeDetail')
#                 except Exception as e:
#                     self.message_user(request, f"Gagal membaca Excel: {e}", level=messages.ERROR)
#                     return redirect('..')

#                 # Import Income
#                 created_inc = 0
#                 for _, row in df_inc.iterrows():
#                     obj, created = Income.objects.update_or_create(
#                         id=row['id'],
#                         defaults={
#                             'project_id': row['project'],
#                             'received_from': row['received_from'],
#                             'total': row.get('total') or 0,
#                             'category': row['category'],
#                             'payment_date': row['payment_date'],
#                             'notes': row.get('notes') or '',
#                         }
#                     )
#                     if created: created_inc += 1

#                 # Import IncomeDetail
#                 created_det = 0
#                 for _, row in df_det.iterrows():
#                     obj, created = IncomeDetail.objects.update_or_create(
#                         id=row['id'],
#                         defaults={
#                             'income_id': row['income'],
#                             'name': row['name'],
#                             'quantity': row.get('quantity') or 0,
#                             'unit_price': row.get('unit_price') or 0,
#                             'unit': row['unit'],
#                             'subtotal': row.get('subtotal') or 0,
#                             'discount': row.get('discount') or 0,
#                             'discount_type': row.get('discount_type'),
#                             'discount_amount': row.get('discount_amount') or 0,
#                             'total': row.get('total') or 0,
#                             'notes': row.get('notes') or '',
#                         }
#                     )
#                     if created: created_det += 1

#                 self.message_user(
#                     request,
#                     f"Sukses import: {created_inc} Income baru, {created_det} IncomeDetail baru.",
#                     level=messages.SUCCESS
#                 )
#                 return redirect('..')
#         else:
#             form = MultiSheetImportForm()

#         context = dict(
#             self.admin_site.each_context(request),
#             form=form,
#             title="Import Income & Details dari Excel"
#         )
#         return render(request, "admin/import_all_income.html", context)
    
#     def display_photo(self, obj):
#         if obj.payment_proof:
#             return format_html('<img src="{}" width="50" height="50" />'.format(obj.payment_proof.url))
#         else:
#             return mark_safe('<span>No Image</span>')
#     display_photo.short_description = 'Photo'

@admin.register(FinanceData)
class FinanceAdmin(
    LedgerSpreadsheetAdminMixin,
    LedgerBalanceAdminMixin,
    SoftDeleteAdminMixin,
    ImportExportMixin,
    ModelAdmin,
):
    spreadsheet_form_class = FinanceDataSpreadsheetRowForm
    spreadsheet_title = 'Finance Ledger · Spreadsheet Input Mode'
    spreadsheet_description = (
        'Masukkan transaksi ledger dalam banyak baris. Bukti foto bersifat '
        'opsional; saldo setiap project atau ledger lain dihitung sekali '
        'setelah seluruh baris berhasil disimpan.'
    )
    import_form_class = ImportForm
    export_form_class = ExportForm
    admin_select_related = ('project',)
    autocomplete_fields = ('project',)
    resource_class = FinanceDataResource
    list_display = (
        'project', 'display_photo_view', 'other', 'date', 'description',
        'debet', 'credit', 'balance', 'is_reconciled', 'is_deleted',
    )
    list_filter = (
        'project', ('date', RangeDateFilter), ('debet', RangeNumericFilter),
        ('credit', RangeNumericFilter), ('balance', RangeNumericFilter),
        'is_reconciled', 'is_deleted',
    )
    search_fields   = ('other', 'description')
    actions = [
        'restore_selected', 'reconcile_selected', 'unreconcile_selected',
    ]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'other', 'date', 'description', 'debet', 'credit', 'balance', ('photo_proof', 'display_photo')
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = (
        'display_photo', 'balance',
        'is_reconciled', 'reconciled_by', 'reconciled_at',
        'created_by', 'created_at', 'updated_by', 'updated_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada Photo Proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo_proof:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo_proof.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected finance data")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

@admin.register(PettyCash)
class PettyCashAdmin(
    LedgerSpreadsheetAdminMixin,
    LedgerBalanceAdminMixin,
    SoftDeleteAdminMixin,
    ImportExportMixin,
    ModelAdmin,
):
    spreadsheet_form_class = PettyCashSpreadsheetRowForm
    spreadsheet_title = 'Petty Cash · Spreadsheet Input Mode'
    spreadsheet_description = (
        'Masukkan beberapa transaksi petty cash sekaligus. Setiap baris '
        'memerlukan tipe, metode pembayaran, dan foto bukti.'
    )
    import_form_class = ImportForm
    export_form_class = ExportForm
    admin_select_related = ('project', 'type', 'payment_via')
    autocomplete_fields = ('project', 'type', 'payment_via')
    resource_class = PettyCashResource
    list_display = (
        'project', 'display_photo_view', 'other', 'date', 'description',
        'type', 'payment_via', 'debet', 'credit', 'balance',
        'is_reconciled', 'is_deleted',
    )
    list_filter = (
        'project', 'type', 'payment_via', ('date', RangeDateFilter),
        ('debet', RangeNumericFilter), ('credit', RangeNumericFilter),
        ('balance', RangeNumericFilter), 'is_reconciled', 'is_deleted',
    )
    search_fields   = ('other', 'description')
    actions = [
        'restore_selected', 'reconcile_selected', 'unreconcile_selected',
    ]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'other', 'date', 'description', 'type', 'payment_via', 'debet', 'credit', 'balance', ('photo_proof', 'display_photo')
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = (
        'display_photo', 'balance',
        'is_reconciled', 'reconciled_by', 'reconciled_at',
        'created_by', 'created_at', 'updated_by', 'updated_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada Photo Proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo_proof:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo_proof.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected petty cash")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")
