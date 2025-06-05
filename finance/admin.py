from django.contrib import admin
import nested_admin
from rangefilter.filters import DateRangeFilter, NumericRangeFilter
from .models import *
from project.models import Schedule
from django.utils.html import format_html
from django.utils.safestring import mark_safe

class ScheduleInline(nested_admin.NestedTabularInline):
    model   = Schedule
    extra   = 0
    fields  = (
        'boq_item', 
        'start_date', 
        'end_date', 
        'duration', 
        'duration_in_field', 
        'duration_for_client', 
        'duration_type', 
        'status', 
        'attachment', 
        'notes'
    )

class BillOfQuantityItemDetailInline(nested_admin.NestedTabularInline):
    model   = BillOfQuantityItemDetail
    inlines = [ScheduleInline]
    extra   = 0
    fields  = (
        'item_number',
        'description',
        'quantity',
        'unit_type',
        'unit_price',
        'total_price',
        'work_weight',
        'notes',
    )
    readonly_fields = ('total_price',)

class BillOfQuantityItemInline(nested_admin.NestedTabularInline):
    model   = BillOfQuantityItem
    inlines = [BillOfQuantityItemDetailInline]
    extra   = 0
    fields  = ('item_number', 'title', 'notes')
    show_change_link = True

class SignatureOnBillOfQuantityInline(nested_admin.NestedTabularInline):
    model   = SignatureOnBillOfQuantity
    extra   = 0
    fields  = ('signature', 'photo_proof')

@admin.register(BillOfQuantity)
class BillOfQuantityAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'status', 'start_date', 'end_date', 'total')
    list_filter     = ('status', 'project', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter), ('total', NumericRangeFilter))
    search_fields   = ('project__project_name', 'notes')
    fields          = ('project', 'status', 'work_weight_total', 'total', 'start_date', 'end_date')
    inlines         = [BillOfQuantityItemInline, SignatureOnBillOfQuantityInline]

#
# Inlines for Expense → ExpenseDetail & ExpenseForMaterial
#
class ExpenseDetailInline(nested_admin.NestedTabularInline):
    model   = ExpenseDetail
    extra   = 0
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
    list_display    = ('project', 'display_photo', 'date', 'total')
    list_filter     = ('project', ('date', DateRangeFilter), ('total', NumericRangeFilter))
    search_fields   = ('project__project_name', 'notes')
    fields          = ('project', 'photo_proof', 'date', 'total', 'notes')
    readonly_fields = ('total',)
    inlines         = [ExpenseDetailInline, ExpenseForMaterialInline]
    
    def display_photo(self, obj):
        if obj.photo_proof:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.photo_proof.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

#
# Inlines for Income → IncomeDetail
#
class IncomeDetailInline(nested_admin.NestedTabularInline):
    model   = IncomeDetail
    extra   = 0
    fields  = (
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

@admin.register(Income)
class IncomeAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'display_photo', 'received_from', 'payment_date', 'category', 'total')
    list_filter     = ('project', 'category', ('payment_date', DateRangeFilter), ('total', NumericRangeFilter))
    search_fields   = ('received_from', 'notes')
    fields          = ('project', 'payment_proof', 'received_from', 'category', 'payment_date', 'total', 'notes')
    readonly_fields = ('total',)
    inlines         = [IncomeDetailInline]
    
    def display_photo(self, obj):
        if obj.payment_proof:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.payment_proof.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'
