from django.contrib import admin
from .models import *
from rangefilter.filters import DateRangeFilter, NumericRangeFilter
import nested_admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# ──────────────── Material ────────────────

class MaterialOnProjectInline(nested_admin.NestedTabularInline):
    model         = MaterialOnProject
    extra         = 0
    classes       = ['collapse']
    fields        = (
        'project', ('photo', 'display_photo'), 'stock', 'quantity_used',
        'notes', 'approved_by', 'approved_date'
    )
    # list_filter   = ('project', ('stock', NumericRangeFilter), ('quantity_used', NumericRangeFilter), ('approved_date', DateRangeFilter), 'approved_by')
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
class MaterialAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('code', 'display_photo_view' ,'name', 'brand', 'category', 'unit', 'standart_price')
    fieldsets = (
        (None, {
            "fields": (
                ('photo', 'display_photo'),
                'code', 'name', 'category', 'brand',
                'unit', 'standart_price', 'descriptions'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('display_photo', 'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    inlines         = [MaterialOnProjectInline]
    list_filter     = ('category', 'brand', 'unit', ('standart_price', NumericRangeFilter), 'is_deleted')
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
class MaterialOnProjectAdmin(admin.ModelAdmin):
    list_display    = ('project', 'display_photo_view', 'material', 'stock', 'quantity_used', 'approved_by', 'approved_date')
    list_filter     = ('project', 'material', 'approved_by', ('stock', NumericRangeFilter), 'is_deleted')
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

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('approved_by', 'approved_date')
        
        return list(set(readonly_fields))
    
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

class ToolOnProjectInline(nested_admin.NestedTabularInline):
    model         = ToolOnProject
    extra         = 0
    classes        = ['collapse']
    fields        = (
        'project', 'amount', 'assigned_date', 'returned_date'
    )
    # list_filter   = ('project', ('amount', NumericRangeFilter), ('assigned_date', DateRangeFilter), ('returned_date', DateRangeFilter))
    # search_fields = ('project__project_name',)

@admin.register(Tool)
class ToolAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('name', 'display_photo_view', 'category', 'serial_number', 'amount', 'available')
    inlines       = [ToolOnProjectInline]
    fieldsets     = (
        (None, {
            "fields": (
                'name', ('photo', 'display_photo'), 'category', 'serial_number', 'conditions', 'amount', 'available'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('display_photo', 'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    list_filter   = ('category', ('amount', NumericRangeFilter), ('available', NumericRangeFilter), 'is_deleted')
    search_fields = ('name', 'serial_number', 'conditions')
    actions       = ['restore_selected',]

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

# ──────────────── ToolOnProject ────────────────

@admin.register(ToolOnProject)
class ToolOnProjectAdmin(admin.ModelAdmin):
    list_display  = ('tool', 'project', 'amount', 'assigned_date', 'returned_date')
    list_filter   = ('project', 'tool', ('amount', NumericRangeFilter), ('assigned_date', DateRangeFilter), ('returned_date', DateRangeFilter), 'is_deleted')
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
