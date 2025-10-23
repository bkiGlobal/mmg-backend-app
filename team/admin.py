from django.contrib import admin
from django.utils.html import format_html
from .models import *
from rangefilter.filters import DateRangeFilter
from django.utils.safestring import mark_safe
import mapwidgets
from django.contrib.auth.models import User
from .forms import *


# ──────────────── Team & Members ────────────────

class TeamMemberInline(admin.TabularInline):
    model           = TeamMember
    extra           = 0
    classes         = ['collapse']
    fields          = ('user', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display    = ('name', 'description')
    list_filter     = ('is_deleted',)
    fieldsets = (
        (None, {
            "fields": (
                'name', 'description'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('created_at', 'created_by', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'deleted_by')
    actions         = ['restore_selected',]
    inlines         = [TeamMemberInline]
    search_fields   = ('name', 'description')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected teams")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for member in obj.members.all():
                if member.is_active:
                    member.is_active = False
                    member.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

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
    classes         = ['collapse']
    fields          = ('team', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

class SignatureInline(admin.TabularInline):
    model           = Signature
    extra           = 0
    classes         = ['collapse']
    fields          = (('signature', 'display_photo'), 'expire_at')
    readonly_fields = ('expire_at', 'display_photo')

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.signature:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.signature.url}" target="_blank"><img src="{obj.signature.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada signature"
    display_photo.short_description = 'Signature Saat Ini'

class InitialInline(admin.TabularInline):
    model           = Initial
    extra           = 0
    classes         = ['collapse']
    fields          = (('initial', 'display_photo'), 'expire_at')
    readonly_fields = ('expire_at', 'display_photo')

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.initial:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.initial.url}" target="_blank"><img src="{obj.initial.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada initial"
    display_photo.short_description = 'Initial Saat Ini'

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     # ketika field yang sedang dirender adalah 'initial'
    #     if db_field.name == 'initial':
    #         # filter queryset agar hanya initial milik user yang login
    #         # asumsinya: Initial.user adalah FK ke Profile, 
    #         # dan Profile punya relasi satu-ke-satu dengan request.user
    #         try:
    #             profile = request.user.profile
    #             kwargs['queryset'] = Initial.objects.filter(user=profile)
    #         except Exception:
    #             # kalau user belum punya profile, kosongkan pilihan
    #             kwargs['queryset'] = Initial.objects.none()
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ──────────────── Attendance ────────────────
@admin.register(Attendance)
class AttendanceModelAdmin(admin.ModelAdmin):
    form = AttendanceAdminForm
    list_display    = ('user', 'date', 'check_in', 'check_out', 'status')
    list_filter     = ('user', 'date', 'status', 'is_deleted')
    search_fields   = ('user__full_name', 'status')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'user', 'date', 'status', 
            ),
        }),
        ('CHECK IN/DATANG', {
            'classes': ('collapse',),
            "fields": (
                ('photo_check_in', 'display_check_in_photo'), 'check_in', 'check_in_location'
            ),
        }),
        ('CHECK OUT/PULANG', {
            'classes': ('collapse',),
            "fields": (
                ('photo_check_out', 'display_check_out_photo'), 'check_out', 'check_out_location'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('date', 'check_in', 'check_out', 'status', 'display_check_in_photo', 'display_check_out_photo', 'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
   
    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_check_in_photo(self, obj):
        if obj.photo_check_in:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_check_in.url}" target="_blank"><img src="{obj.photo_check_in.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada foto Check-in"
    display_check_in_photo.short_description = 'Foto Check-in Saat Ini'

    # Poin 1: Metode untuk menampilkan foto Check-out
    def display_check_out_photo(self, obj):
        if obj.photo_check_out:
            return mark_safe(f'<a href="{obj.photo_check_out.url}" target="_blank"><img src="{obj.photo_check_out.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada foto Check-out"
    display_check_out_photo.short_description = 'Foto Check-out Saat Ini'
    # Poin 1 & 4: Mengunci field user dan lokasi
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('user', )
        
        return list(set(readonly_fields))

    # Poin 1: Auto-assign user (Keamanan Server-side)
    def save_model(self, request, obj, form, change):
        # Memastikan field 'user' ditetapkan ke pengguna yang login
        if not request.user.is_superuser and not change:
            try:
                # Asumsi Profile adalah model yang benar untuk FK
                obj.user = request.user.profile 
            except Profile.DoesNotExist:
                # Handle kasus jika user belum memiliki profile
                pass 
        super().save_model(request, obj, form, change)
    
    # Memasukkan request ke form kustom
    # def get_form(self, request, obj=None, **kwargs):
    #     Form = super().get_form(request, obj, **kwargs)
    #     # Periksa apakah pengguna adalah superuser
    #     if request.user.is_superuser or obj is None:
    #         # Jika superuser, gunakan widget interaktif (GoogleMapPointFieldWidget)
    #         self.formfield_overrides[gis_models.PointField]['widget'] = mapwidgets.GoogleMapPointFieldWidget
    #     else:
    #         # Jika bukan superuser, gunakan widget statis (GoogleMapPointFieldStaticWidget)
    #         self.formfield_overrides[gis_models.PointField]['widget'] = mapwidgets.GoogleMapPointFieldStaticWidget
    #     # Menghapus formfield_for_foreignkey user di sini karena save_model sudah menjamin keamanan
        
    #     # Kelas sementara untuk menyuntikkan objek request ke Form __init__
    #     class AttendanceFormWithRequest(Form):
    #         def __init__(self, *args, **kwargs):
    #             kwargs['request'] = request
    #             super().__init__(*args, **kwargs)
    #     return AttendanceFormWithRequest

    # Poin 4: Integrasi JavaScript kustom
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.js',
            settings.STATIC_URL + 'admin/js/attendance_admin.js',  # File JS custom di static/js/
        )
    # Override formfield_overrides untuk location (hanya untuk superuser)
    formfield_overrides = {
        gis_models.PointField: {
            'widget': mapwidgets.GoogleMapPointFieldWidget  # Atau OSMWidget jika tidak pakai Google
        }
    }

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
        if not request.user.is_superuser:
            if db_field.name == 'user':
                try:
                    user = request.user
                    kwargs['queryset'] = User.objects.filter(pk=user.pk)
                except Exception:
                    # kalau user belum punya profile, kosongkan pilihan
                    kwargs['queryset'] = User.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Non-superuser: hanya lihat record miliknya
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' not in request.GET:
            # Tanpa param, otomatis filter hanya yang is_deleted=False
            qs.filter(is_deleted=False)
        # Superuser boleh lihat semua
        if request.user.is_superuser:
            return qs
        return qs.filter(user__user=request.user)
    
    @admin.action(description="Restore selected attendances")
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

# ──────────────── Attendance ────────────────
class AttendanceInline(admin.TabularInline):
    model           = Attendance
    extra           = 1
    classes         = ['collapse',]
    fields          = ('date', 'check_in', 'check_out', 'check_in_location', 'check_out_location', 'status', 'photo_check_in', 'photo_check_out')
    readonly_fields = ('date', 'check_in', 'check_out', 'status')

    formfield_overrides = {
        gis_models.PointField: {'widget': mapwidgets.GoogleMapPointFieldWidget}
    }
    
class LeaveRequestInline(admin.TabularInline):
    model           = LeaveRequest
    extra           = 0
    classes         = ['collapse',]
    fk_name         = 'user'
    fields          = ('status', 'start_date', 'end_date', 'reason', ('photo_proof', 'display_photo'), 'approved_by', 'approved_date')
    readonly_fields = ('display_photo', 'status')

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display    = ('full_name', 'display_photo_view', 'user', 'role', 'gender', 'status', 'phone_number', 'is_active')
    inlines         = [TeamMemberInline, SignatureInline, InitialInline, AttendanceInline, LeaveRequestInline]
    fieldsets = (
        (None, {
            "fields": (
                ('profile_picture', 'display_photo'),
                'user', 'location', 'full_name', 'role',
                'gender', 'status', 'birthday',
                'join_date', 'phone_number', 
                'is_active'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    list_filter     = ('role', 'gender', 'status', 'is_active', ('birthday', DateRangeFilter), ('join_date', DateRangeFilter), 'is_deleted')
    search_fields   = ('full_name', 'phone_number')
    readonly_fields = ('display_photo', 'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    
    def display_photo(self, obj):
        if obj.profile_picture:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.profile_picture.url}" target="_blank"><img src="{obj.profile_picture.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada profile picture"
    display_photo.short_description = 'Profile Picture Saat Ini'

    def display_photo_view(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" />'.format(obj.profile_picture.url))
        else:
            return mark_safe('<span>No Image</span>')
    display_photo.short_description = 'Photo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Non-superuser: hanya lihat record miliknya
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' not in request.GET:
            # Tanpa param, otomatis filter hanya yang is_deleted=False
            qs.filter(is_deleted=False)
        # Superuser boleh lihat semua
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('is_active', )
        
        return list(set(readonly_fields))
    
    @admin.action(description="Restore selected profiles")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for member in obj.team_members.all():
                if member.is_active:
                    member.is_active = False
                    member.save()
            for signature in obj.signatures.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
            for initial in obj.initials.all():
                if initial.is_deleted:
                    initial.is_deleted = False
                    initial.deleted_at = None
                    initial.deleted_by = None
                    initial.save()
            for attendance in obj.user_attendance.all():
                if attendance.is_deleted:
                    attendance.is_deleted = False
                    attendance.deleted_at = None
                    attendance.deleted_by = None
                    attendance.save()
            for leave_req in obj.user_leave_request.all():
                if leave_req.is_deleted:
                    leave_req.is_deleted = False
                    leave_req.deleted_at = None
                    leave_req.deleted_by = None
                    for leave_req_signature in leave_req.leave_request_signatures.all():
                        if leave_req_signature.is_deleted:
                            leave_req_signature.is_deleted = False
                            leave_req_signature.deleted_at = None
                            leave_req_signature.deleted_by = None
                            leave_req_signature.save()
                    leave_req.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

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

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display    = ('user' ,'status', 'display_photo_view', 'start_date', 'end_date', 'reason', 'approved_by', 'approved_date')
    list_filter     = ('user' ,'status', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter), ('approved_date', DateRangeFilter), 'approved_by', 'is_deleted')
    search_fields   = ('reason', )
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'user' ,'status', 'start_date', 'end_date', 'reason', ('photo_proof', 'display_photo')
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    readonly_fields = ('display_photo', 'approved_by', 'approved_date', 'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')

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

    def save_model(self, request, obj, form, change):
        # Jika status diubah dan baru saja menjadi Approved
        if change:
            previous = self.model.objects.get(pk=obj.pk)
            if previous.status != obj.status and obj.status == LeaveStatus.APPROVED:
                obj.approve_by = request.user
                obj.approve_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('status', )
        
        return list(set(readonly_fields))

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == LeaveStatus.APPROVED:  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnLeaveRequestInline(self.model, self.admin_site))

        return inline_instances
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Non-superuser: hanya lihat record miliknya
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' not in request.GET:
            # Tanpa param, otomatis filter hanya yang is_deleted=False
            qs.filter(is_deleted=False)
        # Superuser boleh lihat semua
        if request.user.is_superuser:
            return qs
        return qs.filter(user__user=request.user)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ketika field yang sedang dirender adalah 'signature'
        if not request.user.is_superuser:
            if db_field.name == 'user':
                try:
                    user = request.user
                    kwargs['queryset'] = Profile.objects.filter(user=user)
                except Exception:
                    # kalau user belum punya profile, kosongkan pilihan
                    kwargs['queryset'] = Profile.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    @admin.action(description="Restore selected leave requests")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for leave_req_signature in obj.leave_request_signatures.all():
                if leave_req_signature.is_deleted:
                    leave_req_signature.is_deleted = False
                    leave_req_signature.deleted_at = None
                    leave_req_signature.deleted_by = None
                    leave_req_signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

# ──────────────── Notifications ────────────────

@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    list_display    = ('title', 'user', 'is_read', 'sent_at')
    list_filter     = ('is_read', ('sent_at', DateRangeFilter))
    search_fields   = ('title', 'user__full_name', 'message')
    readonly_fields = ('id', 'sent_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superuser boleh lihat semua
        if request.user.is_superuser:
            return qs
        # Non-superuser: hanya lihat record miliknya
        return qs.filter(user__user=request.user)

# ──────────────── SubContractor & Workers ────────────────

class SubContractorWorkerInline(admin.TabularInline):
    model = SubContractorWorker
    extra = 0
    classes = ['collapse',]
    fields = ('worker_name', 'contact_number', ('id_photo', 'display_photo'))
    readonly_fields = ('display_photo',)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.id_photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.id_photo.url}" target="_blank"><img src="{obj.id_photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo"
    display_photo.short_description = 'Photo Saat Ini'

class SubContractorOnProjectInline(admin.TabularInline):
    model  = SubContractorOnProject
    extra  = 0
    classes = ['collapse',]
    fields = ('project', 'is_active', 'descriptions')

@admin.register(SubContractor)
class SubContractorAdmin(admin.ModelAdmin):
    list_display    = ('name', 'locations', 'contact_person', 'contact_number', 'email')
    list_filter     = ('is_deleted', )
    inlines         = [SubContractorWorkerInline, SubContractorOnProjectInline]
    fieldsets = (
        (None, {
            "fields": (
                'name', 'locations', 'contact_person', 'contact_number', 'email', 'descriptions'
            ),
        }),
        ('METADATA', {
            'classes': ('collapse',),
            "fields": (
                'updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by'
            ),
        }),
    )
    search_fields   = ('name', 'locations__name', 'contact_person', 'contact_number', 'email', 'descriptions')
    actions         = ['restore_selected',]
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at', 'is_deleted', 'deleted_at', 'deleted_by')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected subcontractors")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for worker in obj.workers.all():
                if worker.is_deleted:
                    worker.is_deleted = False
                    worker.deleted_at = None
                    worker.deleted_by = None
                    worker.save()
            for project in obj.subcontractors_on_project.all():
                if project.is_deleted:
                    project.is_deleted = False
                    project.deleted_at = None
                    project.deleted_by = None
                    project.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

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