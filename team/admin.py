from django.contrib import admin
from django.utils.html import format_html
from .models import *
from rangefilter.filters import DateRangeFilter
from django.utils.safestring import mark_safe
import mapwidgets


# ──────────────── Team & Members ────────────────

class TeamMemberInline(admin.TabularInline):
    model           = TeamMember
    extra           = 0
    fields          = ('user', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display   = ('name', 'description')
    fields         = ('name', 'description')
    inlines        = [TeamMemberInline]
    search_fields  = ('name', 'description')


# @admin.register(TeamMember)
# class TeamMemberAdmin(admin.ModelAdmin):
#     list_display   = ('user', 'team', 'is_active', 'timestamp')
#     list_filter    = ('team', 'is_active')
#     search_fields  = ('user__full_name', 'team__name')
#     readonly_fields = ('id', 'timestamp')

# ──────────────── Profile ────────────────

class TeamMemberInline(admin.TabularInline):
    model           = TeamMember
    extra           = 0
    fields          = ('team', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

class SignatureInline(admin.TabularInline):
    model           = Signature
    extra           = 0
    fields          = ('signature', 'expire_at')
    readonly_fields = ('expire_at',)

class InitialInline(admin.TabularInline):
    model           = Initial
    extra           = 0
    fields          = ('initial', 'expire_at')
    readonly_fields = ('expire_at',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'initial'
        if db_field.name == 'initial':
            # filter queryset agar hanya initial milik user yang login
            # asumsinya: Initial.user adalah FK ke Profile, 
            # dan Profile punya relasi satu-ke-satu dengan request.user
            try:
                profile = request.user.profile
                kwargs['queryset'] = Initial.objects.filter(user=profile)
            except Exception:
                # kalau user belum punya profile, kosongkan pilihan
                kwargs['queryset'] = Initial.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# ──────────────── Attendance ────────────────
class AttendanceInline(admin.TabularInline):
    model           = Attendance
    extra           = 1
    fields          = ('date', 'check_in', 'check_out', 'check_in_location', 'check_out_location', 'status', 'photo_check_in', 'photo_check_out')

    formfield_overrides = {
        gis_models.PointField: {'widget': mapwidgets.GoogleMapPointFieldWidget}
    }
    
class LeaveRequestInline(admin.TabularInline):
    model           = LeaveRequest
    extra           = 0
    fk_name         = 'user'
    fields          = ('status', 'start_date', 'end_date', 'reason', 'photo_proof', 'approved_by', 'approved_date')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display    = ('full_name', 'display_photo', 'user', 'role', 'gender', 'status', 'phone_number', 'is_active')
    inlines         = [TeamMemberInline, SignatureInline, InitialInline, AttendanceInline, LeaveRequestInline]
    fields          = (
        'location', 'user', 'full_name', 'role',
        'gender', 'status', 'birthday',
        'join_date', 'phone_number', 'profile_picture',
        'is_active', 'update_at'
    )
    list_filter     = ('role', 'gender', 'status', 'is_active', ('birthday', DateRangeFilter), ('join_date', DateRangeFilter))
    search_fields   = ('full_name', 'phone_number')
    readonly_fields = ('update_at', )
    
    def display_photo(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.profile_picture.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

# ──────────────── Signature & Initial ────────────────

# @admin.register(Signature)
# class SignatureAdmin(admin.ModelAdmin):
#     list_display   = ('user', 'expire_at', 'created_at')
#     list_filter    = ('expire_at',)
#     search_fields  = ('user__full_name',)
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# @admin.register(Initial)
# class InitialAdmin(admin.ModelAdmin):
#     list_display   = ('user', 'expire_at', 'created_at')
#     list_filter    = ('expire_at',)
#     search_fields  = ('user__full_name',)
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# ──────────────── LeaveRequests ────────────────

class SignatureOnLeaveRequestInline(admin.TabularInline):
    model   = SignatureOnLeaveRequest
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

@admin.register(LeaveRequest)
class LeaveRequestInline(admin.ModelAdmin):
    list_display    = ('status', 'start_date', 'end_date', 'reason', 'photo_proof', 'approved_by', 'approved_date')
    list_filter     = ('status', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter), ('approved_date', DateRangeFilter), 'approved_by')
    search_fields   = ('reason', )
    fields          = ('status', 'start_date', 'end_date', 'reason', 'photo_proof')
    readonly_fields = ('approved_by', 'approved_date')

    def save_model(self, request, obj, form, change):
        # Jika status diubah dan baru saja menjadi Approved
        if change:
            previous = self.model.objects.get(pk=obj.pk)
            if previous.status != obj.status and obj.status == LeaveStatus.APPROVED:
                obj.approve_by = request.user
                obj.approve_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == LeaveStatus.APPROVED:  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnLeaveRequestInline(self.model, self.admin_site))

        return inline_instances

# ──────────────── Notifications ────────────────

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display    = ('title', 'user', 'is_read', 'sent_at')
    list_filter     = ('is_read', ('sent_at', DateRangeFilter))
    search_fields   = ('title', 'user__full_name', 'message')
    readonly_fields = ('id', 'sent_at')

# ──────────────── SubContractor & Workers ────────────────

class SubContractorWorkerInline(admin.TabularInline):
    model = SubContractorWorker
    extra = 0
    fields = ('worker_name', 'contact_number', 'id_photo')

class SubContractorOnProjectInline(admin.TabularInline):
    model  = SubContractorOnProject
    extra  = 0
    fields = ('project', 'is_active', 'descriptions')

@admin.register(SubContractor)
class SubContractorAdmin(admin.ModelAdmin):
    list_display    = ('name', 'locations', 'contact_person', 'contact_number', 'email')
    inlines         = [SubContractorWorkerInline, SubContractorOnProjectInline]
    fields          = ('name', 'locations', 'contact_person', 'contact_number', 'email', 'descriptions')
    search_fields   = ('name', 'locations__name', 'contact_person', 'contact_number', 'email', 'descriptions')

# @admin.register(SubContractorWorker)
# class SubContractorWorkerAdmin(admin.ModelAdmin):
#     list_display   = ('worker_name', 'subcon', 'contact_number')
#     list_filter    = ('subcon',)
#     search_fields  = ('worker_name', 'subcon__name')
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# ──────────────── SubContractorOnProject ────────────────

# @admin.register(SubContractorOnProject)
# class SubContractorOnProjectAdmin(admin.ModelAdmin):
#     list_display   = ('subcon', 'project', 'is_active')
#     list_filter    = ('subcon', 'project', 'is_active')
#     search_fields  = ('subcon__name', 'project__project_name')
#     readonly_fields = ('id',)
#     fieldsets = (
#         (None, {
#             'fields': (
#                 'project', 'subcon', 'is_active', 'descriptions'
#             )
#         }),
#         ('Audit Info', {
#             'classes': ('collapse',),
#             'fields': ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'deleted_by')
#         }),
#     )