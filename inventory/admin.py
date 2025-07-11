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
    fields        = (
        'project', 'photo', 'stock', 'quantity_used',
        'notes', 'approved_by', 'approved_date'
    )
    # list_filter   = ('project', ('stock', NumericRangeFilter), ('quantity_used', NumericRangeFilter), ('approved_date', DateRangeFilter), 'approved_by')
    # search_fields = ('project__project_name', 'notes')

@admin.register(Material)
class MaterialAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('code', 'name', 'brand', 'category', 'unit', 'standart_price')
    fields        = (
        'code', 'name', 'category', 'brand',
        'unit', 'standart_price', 'descriptions',
    )
    inlines       = [MaterialOnProjectInline]
    list_filter   = ('category', 'brand', 'unit', ('standart_price', NumericRangeFilter))
    search_fields = ('code', 'name', 'descriptions')


# ──────────────── MaterialOnProject ────────────────

# @admin.register(MaterialOnProject)
# class MaterialOnProjectAdmin(admin.ModelAdmin):
#     list_display  = ('project', 'material', 'stock', 'quantity_used', 'approved_by', 'approved_date')
#     list_filter   = ('project', 'material', 'approved_by')
#     search_fields = ('project__project_name', 'material__name')
#     readonly_fields = ('id',)
#     date_hierarchy = 'approved_date'
#     fieldsets = (
#         (None, {
#             'fields': (
#                 'project', 'material',
#                 'stock', 'quantity_used',
#                 'notes',
#             )
#         }),
#         ('Approval', {
#             'fields': ('approved_by', 'approved_date')
#         }),
#         ('Audit Info', {
#             'classes': ('collapse',),
#             'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
#         }),
#     )


# ──────────────── Tool ────────────────

class ToolOnProjectInline(nested_admin.NestedTabularInline):
    model         = ToolOnProject
    extra         = 0
    fields        = (
        'project', 'amount', 'assigned_date', 'returned_date'
    )
    list_filter   = ('project', ('amount', NumericRangeFilter), ('assigned_date', DateRangeFilter), ('returned_date', DateRangeFilter))
    search_fields = ('project__project_name',)

@admin.register(Tool)
class ToolAdmin(nested_admin.NestedModelAdmin):
    list_display  = ('name', 'display_photo', 'category', 'serial_number', 'amount', 'available')
    inlines       = [ToolOnProjectInline]
    fields        = ('name', 'photo', 'category', 'serial_number', 'conditions', 'amount', 'available')
    list_filter   = ('category', ('amount', NumericRangeFilter), ('available', NumericRangeFilter))
    search_fields = ('name', 'serial_number', 'conditions')

    def display_photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

# ──────────────── ToolOnProject ────────────────

# @admin.register(ToolOnProject)
# class ToolOnProjectAdmin(admin.ModelAdmin):
#     list_display  = ('tool', 'project', 'amount', 'assigned_date', 'returned_date')
#     list_filter   = ('project', 'tool')
#     search_fields = ('tool__name', 'project__project_name')
#     readonly_fields = ('id',)
#     date_hierarchy = 'assigned_date'
#     fieldsets = (
#         (None, {
#             'fields': (
#                 'project', 'tool', 'amount',
#             )
#         }),
#         ('Dates', {
#             'fields': ('assigned_date', 'returned_date')
#         }),
#         ('Audit Info', {
#             'classes': ('collapse',),
#             'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted')
#         }),
#     )
