from django.contrib import admin, messages
from decimal import Decimal
from .models import *
from unfold.contrib.filters.admin import RangeDateFilter, RangeNumericFilter
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from core.admin_mixins import (
    ApprovalWorkflowAdminMixin,
    ProjectAutocompleteFilterAdminMixin,
    SoftDeleteAdminMixin,
)
from unfold.admin import ModelAdmin, TabularInline
from .services import complete_tool_maintenance, receive_purchase_request

# ──────────────── Material ────────────────

class MaterialOnProjectInline(TabularInline):
    tab = True
    model         = MaterialOnProject
    extra         = 0
    classes       = ['collapse']
    fields        = (
        'project', ('photo', 'display_photo'), 'stock', 'quantity_used',
        'notes', 'approved_by', 'approved_date'
    )
    # list_filter   = ('project', ('stock', RangeNumericFilter), ('quantity_used', RangeNumericFilter), ('approved_date', RangeDateFilter), 'approved_by')
    # search_fields = ('project__project_name', 'notes')
    readonly_fields = ('display_photo', 'approved_by', 'approved_date')

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo.url}" target="_blank"><img src="{obj.photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo"
    display_photo.short_description = 'Photo Saat Ini'

@admin.register(Material)
class MaterialAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('category', 'brand', 'unit')
    autocomplete_fields = ('category', 'brand', 'unit')
    list_display = (
        'code', 'display_photo_view', 'name', 'brand', 'category',
        'unit', 'standart_price', 'minimum_stock',
    )
    fieldsets = (
        (None, {
            "fields": (
                ('photo', 'display_photo'),
                'code', 'name', 'category', 'brand',
                'unit', 'standart_price', 'minimum_stock', 'descriptions'
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
        'display_photo',
        'updated_by', 'updated_at', 'created_by', 'created_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    inlines         = [MaterialOnProjectInline]
    list_filter     = ('category', 'brand', 'unit', ('standart_price', RangeNumericFilter), 'is_deleted')
    search_fields   = ('code', 'name', 'descriptions')
    actions         = ['restore_selected',]

    def display_photo(self, obj):
        if obj.photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo.url}" target="_blank"><img src="{obj.photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo"
    display_photo.short_description = 'Photo Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo.url))
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
    
    @admin.action(description="Restore selected materials")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for material in obj.material_project.all():
                if material.is_deleted:
                    material.is_deleted = False
                    material.deleted_at = None
                    material.deleted_by = None
                    material.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

# ──────────────── MaterialOnProject ────────────────

@admin.register(MaterialOnProject)
class MaterialOnProjectAdmin(
    ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin, ModelAdmin
):
    approval_workflow_type = 'project_material'
    approval_required_role = 'logistic,pm'
    admin_select_related = ('project', 'material', 'approved_by')
    autocomplete_fields = ('project', 'material')
    list_display = (
        'project', 'display_photo_view', 'material', 'stock_health',
        'quantity_used', 'approved_by', 'approved_date',
    )
    list_filter     = ('project', 'material', 'approved_by', ('stock', RangeNumericFilter), 'is_deleted')
    search_fields   = ('project__project_name', 'material__name')
    readonly_fields = ('id', 'display_photo', 'created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
    date_hierarchy  = 'created_at'
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            'fields': (
                'project', 'material',
                ('photo', 'display_photo'), 'stock', 
                'quantity_used', 'notes',
            )
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_date')
        }),
        ('Audit Info', {
            'classes': ('collapse',),
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    def display_photo(self, obj):
        if obj.photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo.url}" target="_blank"><img src="{obj.photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo"
    display_photo.short_description = 'Photo Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    @admin.display(description='Ketersediaan stok', ordering='stock')
    def stock_health(self, obj):
        available = obj.available_stock
        minimum = (
            obj.material.minimum_stock
            if obj.material_id
            else Decimal('0')
        )
        if available < minimum:
            tone = 'danger'
            label = 'Stok rendah'
        elif minimum and available <= minimum * Decimal('1.25'):
            tone = 'warning'
            label = 'Mendekati minimum'
        else:
            tone = 'success'
            label = 'Stok aman'
        if minimum:
            width = min(float(available / minimum * 100), 100)
        else:
            width = 100 if available else 0
        unit = obj.material.unit if obj.material_id else ''
        return format_html(
            '<span class="mmg-stock-indicator mmg-stock-indicator--{}">'
            '<span class="mmg-stock-indicator__meta">'
            '<strong>{} {}</strong><small>{}</small></span>'
            '<span class="mmg-stock-indicator__track">'
            '<i style="width: {}%"></i></span></span>',
            tone,
            available,
            unit,
            label,
            width,
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('approved_by', 'approved_date')
        
        return list(set(readonly_fields))

    def save_model(self, request, obj, form, change):
        profile = getattr(request.user, 'profile', None)
        if profile:
            obj.approved_by = profile
            obj.approved_date = timezone.now()
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected materials")
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

# ──────────────── Tool ────────────────

class ToolOnProjectInline(TabularInline):
    tab = True
    model         = ToolOnProject
    extra         = 0
    classes        = ['collapse']
    fields        = (
        'project', 'amount', 'assigned_date', 'returned_date'
    )
    # list_filter   = ('project', ('amount', RangeNumericFilter), ('assigned_date', RangeDateFilter), ('returned_date', RangeDateFilter))
    # search_fields = ('project__project_name',)


class ToolMaintenanceInline(TabularInline):
    tab = True
    model = ToolMaintenance
    extra = 0
    fields = (
        'scheduled_date', 'status', 'completed_date', 'cost', 'notes',
    )
    readonly_fields = ('status', 'completed_date')

@admin.register(Tool)
class ToolAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('category',)
    autocomplete_fields = ('category',)
    list_display = (
        'name', 'display_photo_view', 'category', 'serial_number',
        'utilization_overview', 'maintenance_state',
    )
    inlines = [ToolOnProjectInline, ToolMaintenanceInline]
    fieldsets     = (
        (None, {
            "fields": (
                'name', ('photo', 'display_photo'), 'category',
                'serial_number', 'conditions', 'amount', 'available',
                'maintenance_interval_days', 'last_maintenance_date',
                'next_maintenance_date', 'is_under_maintenance',
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
        'display_photo', 'available', 'is_under_maintenance',
        'updated_by', 'updated_at', 'created_by', 'created_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    list_filter   = ('category', ('amount', RangeNumericFilter), ('available', RangeNumericFilter), 'is_deleted')
    search_fields = ('name', 'serial_number', 'conditions')
    actions       = ['restore_selected',]

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    def display_photo(self, obj):
        if obj.photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo.url}" target="_blank"><img src="{obj.photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo"
    display_photo.short_description = 'Photo Saat Ini'

    def display_photo_view(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    @admin.display(description='Utilisasi', ordering='available')
    def utilization_overview(self, obj):
        allocated = max(obj.amount - obj.available, 0)
        percentage = (
            min(round(allocated / obj.amount * 100), 100)
            if obj.amount
            else 0
        )
        return format_html(
            '<span class="mmg-utilization">'
            '<span><strong>{}%</strong>'
            '<small>{} dipakai · {} tersedia</small></span>'
            '<span class="mmg-utilization__track">'
            '<i style="width: {}%"></i></span></span>',
            percentage,
            allocated,
            obj.available,
            percentage,
        )

    @admin.display(
        description='Maintenance',
        boolean=True,
        ordering='is_under_maintenance',
    )
    def maintenance_state(self, obj):
        return obj.is_under_maintenance
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected tools")
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


@admin.register(StockMovement)
class StockMovementAdmin(ProjectAutocompleteFilterAdminMixin, ModelAdmin):
    list_display = (
        'created_at', 'project', 'material', 'movement_type',
        'quantity', 'balance_after', 'reference_type',
    )
    list_filter = (
        'movement_type', 'project', 'material', ('created_at', RangeDateFilter),
    )
    search_fields = (
        'project__project_name', 'material__name',
        'reference_type', 'reference_id', 'notes',
    )
    list_select_related = ('project', 'material')
    readonly_fields = tuple(
        field.name for field in StockMovement._meta.fields
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(
    ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin, ModelAdmin
):
    approval_workflow_type = 'purchase_request'
    approval_required_role = 'logistic,pm,cfo'
    list_display = (
        'material', 'project', 'quantity', 'status',
        'requested_by', 'approved_by', 'created_at',
    )
    list_filter = (
        'status', 'project', 'material', ('created_at', RangeDateFilter),
        'is_deleted',
    )
    search_fields = (
        'material__name', 'material__code',
        'project__project_name', 'notes',
    )
    admin_select_related = (
        'material', 'project', 'requested_by', 'approved_by',
    )
    autocomplete_fields = ('project', 'material')
    readonly_fields = (
        'requested_by', 'approved_by', 'approved_at',
        'ordered_at', 'received_at',
        'created_at', 'created_by', 'updated_at', 'updated_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    actions = ('receive_selected',)

    def save_model(self, request, obj, form, change):
        if not change and not obj.requested_by_id:
            obj.requested_by = getattr(request.user, 'profile', None)
        super().save_model(request, obj, form, change)

    @admin.action(description='Terima barang untuk request terpilih')
    def receive_selected(self, request, queryset):
        received = 0
        for purchase in queryset:
            try:
                receive_purchase_request(purchase, request.user)
                received += 1
            except Exception as exc:
                self.message_user(request, str(exc), level=messages.ERROR)
        self.message_user(request, f'{received} purchase request diterima.')


@admin.register(ToolMaintenance)
class ToolMaintenanceAdmin(SoftDeleteAdminMixin, ModelAdmin):
    list_display = (
        'tool', 'scheduled_date', 'status', 'completed_date', 'cost',
    )
    list_filter = (
        'status', ('scheduled_date', RangeDateFilter),
        ('completed_date', RangeDateFilter), 'is_deleted',
    )
    search_fields = ('tool__name', 'tool__serial_number', 'notes')
    admin_select_related = ('tool',)
    autocomplete_fields = ('tool',)
    readonly_fields = (
        'completed_date',
        'created_at', 'created_by', 'updated_at', 'updated_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    actions = ('complete_selected',)

    @admin.action(description='Selesaikan maintenance terpilih')
    def complete_selected(self, request, queryset):
        completed = 0
        for maintenance in queryset:
            complete_tool_maintenance(maintenance, request.user)
            completed += 1
        self.message_user(request, f'{completed} maintenance diselesaikan.')

# ──────────────── ToolOnProject ────────────────

@admin.register(ToolOnProject)
class ToolOnProjectAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('tool', 'project')
    autocomplete_fields = ('tool', 'project')
    list_display  = ('tool', 'project', 'amount', 'assigned_date', 'returned_date')
    list_filter   = ('project', 'tool', ('amount', RangeNumericFilter), ('assigned_date', RangeDateFilter), ('returned_date', RangeDateFilter), 'is_deleted')
    search_fields = ('tool__name', 'project__project_name')
    readonly_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
    date_hierarchy = 'assigned_date'
    fieldsets = (
        (None, {
            'fields': (
                'project', 'tool', 'amount',
            )
        }),
        ('Dates', {
            'fields': ('assigned_date', 'returned_date')
        }),
        ('Audit Info', {
            'classes': ('collapse',),
            'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected tools")
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
