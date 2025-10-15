from django.contrib import admin, messages
import nested_admin
from rangefilter.filters import DateRangeFilter, NumericRangeFilter
from .models import *
from team.models import Profile
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .resources import *
from import_export.admin import ImportExportMixin, ImportExportModelAdmin
import io
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import *

# class ScheduleInline(nested_admin.NestedTabularInline):
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

# class BillOfQuantityItemDetailInline(nested_admin.NestedTabularInline):
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

# class BillOfQuantitySubItemInline(nested_admin.NestedTabularInline):
#     model   = BillOfQuantitySubItem
#     inlines = [BillOfQuantityItemDetailInline]
#     extra   = 0
#     fields  = ('item_order', 'title', 'notes',)
#     readonly_fields = ('total_price',)

# class BillOfQuantityItemInline(nested_admin.NestedTabularInline):
#     model   = BillOfQuantityItem
#     inlines = [BillOfQuantitySubItemInline]
#     extra   = 0
#     fields  = ('item_number', 'title', 'notes')
#     show_change_link = True

class SignatureOnBillOfQuantityInline(nested_admin.NestedTabularInline):
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

class BillOfQuantityVersionInline(nested_admin.NestedTabularInline):
    model           = BillOfQuantityVersion
    extra           = 0
    classes         = ['collapse']
    fields          = ('title', 'document_number', 'boq_file', 'status', 'total', 'notes')

@admin.register(BillOfQuantity)
class BillOfQuantityAdmin(ImportExportMixin, nested_admin.NestedModelAdmin):
    list_display    = ('project', 'document_name', 'status', 'issue_date', 'due_date', 'is_deleted')
    list_filter     = ('project', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter), 'approval_required', 'approval_level', 'is_deleted')
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

class SignatureOnPaymentRequestInline(nested_admin.NestedTabularInline):
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

class PaymentRequestVersionInline(nested_admin.NestedTabularInline):
    model           = PaymentRequestVersion
    extra           = 0
    classes         = ['collapse',]
    fields          = ('title', 'payment_number', 'payment_file', 'status', 'total', 'notes')

@admin.register(PaymentRequest)
class PaymentRequestAdmin(ImportExportMixin, nested_admin.NestedModelAdmin):
    list_display    = ('project', 'payment_name', 'status', 'issue_date', 'due_date', 'is_deleted')
    list_filter     = ('project', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter), 'approval_required', 'approval_level', 'is_deleted')
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

class ExpenseDetailInline(nested_admin.NestedTabularInline):
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
    readonly_fields = ('subtotal', 'total')

class ExpenseForMaterialInline(nested_admin.NestedTabularInline):
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
    readonly_fields = ('subtotal', 'total')

@admin.register(ExpenseOnProject)
class ExpenseOnProjectAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'display_photo_view', 'date', 'total', 'is_deleted')
    list_filter     = ('project', ('date', DateRangeFilter), ('total', NumericRangeFilter), 'is_deleted')
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
        # 1) export kedua dataset
        expense_ds = ExpenseResource().export()
        detail_ds = ExpenseDetailResource().export()
        material_ds = ExpenseForMaterialResource().export()

        # 2) ubah ke DataFrame pandas
        df_exp = pd.DataFrame(expense_ds.dict)
        df_det = pd.DataFrame(detail_ds.dict)
        df_mat = pd.DataFrame(material_ds.dict)

        # 3) tulis ke Excel multi-sheet
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_exp.to_excel(writer, sheet_name='Expense', index=False)
            df_det.to_excel(writer, sheet_name='ExpenseDetail', index=False)
            df_mat.to_excel(writer, sheet_name='ExpenseForMaterial', index=False)
        buffer.seek(0)

        # 4) kembalikan HttpResponse sebagai file download
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="expepense_full_export.xlsx"'
        return response
    
    def import_all_view(self, request):
        """
        Custom admin view untuk upload dan import file multi‐sheet Excel.
        """
        if request.method == 'POST':
            form = MultiSheetImportForm(request.POST, request.FILES)
            if form.is_valid():
                excel_file = form.cleaned_data['file']
                try:
                    # Baca ketiga sheet
                    xls = pd.ExcelFile(excel_file)
                    df_exp = xls.parse('Expense')
                    df_det = xls.parse('ExpenseDetail')
                    df_mat = xls.parse('ExpenseForMaterial')
                except Exception as e:
                    self.message_user(request, f"Gagal membaca Excel: {e}", level=messages.ERROR)
                    return redirect('..')

                # Import Expense
                created_inc = 0
                for _, row in df_exp.iterrows():
                    obj, created = ExpenseOnProject.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'project_id': row['project'], 
                            'date': row['date'],
                            'total': row.get('total') or 0,
                            'notes': row.get('notes') or '',
                            'photo_proof': row.get('photo_proof') or None,
                        }
                    )
                    if created: created_inc += 1

                # Import ExpenseDetail
                created_det = 0
                for _, row in df_det.iterrows():
                    obj, created = ExpenseDetail.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'expense_on_project_id': row['expense_on_project'],
                            'category': row['category'],
                            'name': row['name'],
                            'quantity': row.get('quantity') or 0,
                            'unit_price': row.get('unit_price') or 0,
                            'unit': row['unit'],
                            'subtotal': row.get('subtotal') or 0,
                            'discount': row.get('discount') or 0,
                            'discount_type': row['discount_type'],
                            'discount_amount': row.get('discount_amount') or 0,
                            'total': row.get('total') or 0,
                            'notes': row.get('notes') or '',
                        }
                    )

                    # Import ExpenseDetail
                created_mat = 0
                for _, row in df_det.iterrows():
                    obj, created = Material.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'expense_on_project_id': row['expense_on_project'],
                            'material': row['material'],
                            'category': row['category'],
                            'quantity': row.get('quantity') or 0,
                            'unit': row['unit'],
                            'unit_price': row.get('unit_price') or 0,
                            'subtotal': row.get('subtotal') or 0,
                            'discount': row.get('discount') or 0,
                            'discount_type': row['discount_type'],
                            'discount_amount': row.get('discount_amount') or 0,
                            'total': row.get('total') or 0,
                        }
                    )

                self.message_user(
                    request,
                    f"Sukses import: {created_inc} Expense baru, {created_det} ExpenseDetail baru, dan ExpenseMaterial {created_mat}.",
                    level=messages.SUCCESS
                )
                return redirect('..')
        else:
            form = MultiSheetImportForm()

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Expense, Details, & Material dari Excel"
        )
        return render(request, "admin/import_all_expense.html", context)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo_proof:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo_proof.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

#
# Inlines for Income → IncomeDetail
#
# class IncomeDetailInline(nested_admin.NestedTabularInline):
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
# class IncomeAdmin(nested_admin.NestedModelAdmin):
#     list_display    = ('project', 'display_photo', 'received_from', 'payment_date', 'category', 'total')
#     list_filter     = ('project', 'category', ('payment_date', DateRangeFilter), ('total', NumericRangeFilter))
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
class FinanceAdmin(ImportExportModelAdmin, nested_admin.NestedModelAdmin):
    resource_class = FinanceDataResource
    list_display    = ('project', 'display_photo_view', 'other', 'date', 'description', 'debet', 'credit', 'balance', 'is_deleted')
    list_filter     = ('project', ('date', DateRangeFilter), ('debet', NumericRangeFilter), ('credit', NumericRangeFilter), ('balance', NumericRangeFilter), 'is_deleted')
    search_fields   = ('other', 'description')
    actions         = ['restore_selected',]
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
    readonly_fields = ('display_photo', 'created_by', 'created_at', 'updated_by', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by')

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
class PettyCashAdmin(ImportExportModelAdmin, nested_admin.NestedModelAdmin):
    resource_class = PettyCashResource
    list_display    = ('project', 'display_photo_view', 'other', 'date', 'description', 'type', 'payment_via', 'debet', 'credit', 'balance', 'is_deleted')
    list_filter     = ('project', 'type', 'payment_via', ('date', DateRangeFilter), ('debet', NumericRangeFilter), ('credit', NumericRangeFilter), ('balance', NumericRangeFilter), 'is_deleted')
    search_fields   = ('other', 'description')
    actions         = ['restore_selected',]
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
    readonly_fields = ('display_photo', 'created_by', 'created_at', 'updated_by', 'updated_at', 'is_deleted', 'deleted_at', 'deleted_by')

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