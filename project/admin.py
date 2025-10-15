import nested_admin
from django.contrib import admin
from team.models import SubContractorOnProject
from finance.models import BillOfQuantity
from .models import *
from .forms import *
from rangefilter.filters import DateRangeFilter, NumericRangeFilter
from django.utils.safestring import mark_safe


# ──────────────── Document & Versions ────────────────

class DocumentVersionInline(nested_admin.NestedTabularInline):
    model           = DocumentVersion
    extra           = 0
    classes         = ['collapse']
    fields          = ('title', 'document_number', 'document_file', 'status', 'notes', 'comment', 
                       'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')

class SignatureOnDocumentInline(nested_admin.NestedTabularInline):
    model           = SignatureOnDocument
    extra           = 0
    classes         = ['collapse']
    fields          = ('signature', ('photo_proof', 'display_photo'))
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

@admin.register(Document)
class DocumentAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'document_name', 'document_type', 'status', 'issue_date', 'due_date')
    list_filter     = ('project', 'document_type', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter), 'approval_required', 'approval_level', 'is_deleted')
    search_fields   = ('project__project_name', 'document_name')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'document_name', 'document_type', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date'
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
    inlines         = [DocumentVersionInline,]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnDocumentInline(self.model, self.admin_site))

        return inline_instances
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected documents")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for version in obj.versions.all():
                if version.is_deleted:
                    version.is_deleted = False
                    version.deleted_at = None
                    version.deleted_by = None
                    version.save()
            for signature in obj.document_signatures.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")
        
# ──────────────── Drawing & Versions ────────────────

class DrawingVersionInline(nested_admin.NestedTabularInline):
    model           = DrawingVersion
    extra           = 0
    classes         = ['collapse',]
    fields          = ('title', 'document_number', 'drawing_file', 'status', 'notes', 'comment', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')

class SignatureOnDrawingInline(nested_admin.NestedTabularInline):
    model   = SignatureOnDrawing
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

@admin.register(Drawing)
class DrawingAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'document_name', 'drawing_type', 'status', 'issue_date', 'due_date')
    list_filter     = ('project', 'drawing_type', 'status', ('issue_date', DateRangeFilter), ('due_date', DateRangeFilter), 'is_deleted')
    search_fields   = ('project__project_name', 'document_name')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'document_name', 'drawing_type', 'status', 'issue_date', 'due_date'
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
    inlines         = [DrawingVersionInline,]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Hanya tambahkan SignatureOnBillOfQuantityInline jika status Approve
        if obj and obj.status == 'approved':  # Sesuaikan jika status choices punya nilai lain
            inline_instances.append(SignatureOnDrawingInline(self.model, self.admin_site))

        return inline_instances
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected drawings")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for version in obj.drawing_versions.all():
                if version.is_deleted:
                    version.is_deleted = False
                    version.deleted_at = None
                    version.deleted_by = None
                    version.save()
            for signature in obj.drawing_signatures.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")
    
# ──────────────── Deflect ────────────────

class DefectDetailInline(nested_admin.NestedTabularInline):
    model   = DefectDetail
    extra   = 0
    classes = ['collapse',]
    fields  = (
        'location_detail', 
        'deviation',
        ('photo', 'display_photo'),
        'initial_checklist_date', 
        'initial_checklist_approval',
        'final_checklist_date',   
        'final_checklist_approval',
        'notes'
    )
    readonly_fields = ('display_photo',)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo.url}" target="_blank"><img src="{obj.photo.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo "
    display_photo.short_description = 'Photo Saat Ini'
    

class SignatureOnDeflectInline(nested_admin.NestedTabularInline):
    model   = SignatureOnDeflect
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

@admin.register(Defect)
class DefectAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'work_title', 'location', 'is_approved', 'approved_at')
    list_filter     = ('project', 'is_approved', ('approved_at', DateRangeFilter), 'is_deleted')
    search_fields   = ('work_title',)
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'work_title', 'location', 'is_approved', 'approved_at'
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
    inlines         = [DefectDetailInline, SignatureOnDeflectInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected defects")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for detail in obj.defect_detail.all():
                if detail.is_deleted:
                    detail.is_deleted = False
                    detail.deleted_at = None
                    detail.deleted_by = None
                    detail.save()
            for signature in obj.defect_signature.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

# ──────────────── ErrorLog & Details ────────────────

class ErrorLogDetailInline(nested_admin.NestedTabularInline):
    model   = ErrorLogDetail
    extra   = 0
    classes = ['collapse',]
    fields  = (
        'date', 
        'descriptions', 
        'solutions',
        'person_in_charge', 
        'open_date', 
        'close_date', 
        ('photo_proof', 'display_photo'), 
        'status'
    )
    readonly_fields = ('display_photo',)

    # Poin 1: Metode untuk menampilkan foto Check-in
    def display_photo(self, obj):
        if obj.photo_proof:
            # Menggunakan mark_safe untuk merender tag HTML
            return mark_safe(f'<a href="{obj.photo_proof.url}" target="_blank"><img src="{obj.photo_proof.url}" style="max-height: 150px; width: auto; border: 1px solid #ccc;" /></a>')
        return "Belum ada photo proof"
    display_photo.short_description = 'Photo Proof Saat Ini'

class SignatureOnErrorLogInline(nested_admin.NestedTabularInline):
    model   = SignatureOnErrorLog
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

@admin.register(ErrorLog)
class ErrorLogAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'work_type', 'periode_start', 'periode_end')
    list_filter     = ('project', 'work_type', ('periode_start', DateRangeFilter), ('periode_end', DateRangeFilter), 'is_deleted')
    search_fields   = ('project__project_name', 'document_number', 'notes')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'document_number', 'work_type', 'periode_start', 'periode_end', 'notes'
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
    inlines         = [ErrorLogDetailInline, SignatureOnErrorLogInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected error logs")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for detail in obj.error_detail.all():
                if detail.is_deleted:
                    detail.is_deleted = False
                    detail.deleted_at = None
                    detail.deleted_by = None
                    detail.save()
            for signature in obj.error_log_signature.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

# ──────────────── WorkMethod & Signatures ────────────────

class SignatureOnWorkMethodInline(nested_admin.NestedTabularInline):
    model   = SignatureOnWorkMethod
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

@admin.register(WorkMethod)
class WorkMethodAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project', 'work_title', 'document_number', 'notes')
    list_filter     = ('project', 'is_deleted')
    search_fields   = ('work_title', 'document_number', 'notes')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'project', 'file', 'work_title', 'document_number', 'notes'
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
    inlines         = [SignatureOnWorkMethodInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected work methods")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for signature in obj.work_method_signature.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")
    
    # def display_photo(self, obj):
    #     if obj.file:
    #         return format_html('<img src="{}" width="50" height="50" />'.format(obj.file.url))
    #     else:
    #         return mark_safe('<span>No Image</span>')
    # display_photo.short_description = 'Photo'

# ──────────────── Project ────────────────

class DocumentInline(nested_admin.NestedTabularInline):
    model           = Document
    extra           = 0
    classes         = ['collapse',]
    fields          = ('document_name', 'document_type', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date')
    inlines         = [DocumentVersionInline, SignatureOnDocumentInline]

class DeflectInline(nested_admin.NestedTabularInline):
    model   = Defect
    extra   = 0
    classes = ['collapse',]
    fields  = ('work_title', 'location', 'is_approved', 'approved_at')
    inlines = [DefectDetailInline, SignatureOnDeflectInline]

class ErrorLogInline(nested_admin.NestedTabularInline):
    model   = ErrorLog
    extra   = 0
    classes = ['collapse',]
    fields  = ('document_number', 'work_type', 'periode_start', 'periode_end', 'notes')
    inlines = [ErrorLogDetailInline, SignatureOnErrorLogInline]

class WorkMethodInline(nested_admin.NestedTabularInline):
    model   = WorkMethod
    extra   = 0
    classes = ['collapse',]
    fields  = ('work_title', 'document_number', 'file', 'notes')
    inlines = [SignatureOnWorkMethodInline,]

class ProgressReportInline(nested_admin.NestedTabularInline):
    model           = ProgressReport
    extra           = 0
    classes         = ['collapse',]
    fields          = ('boq_item', 'type', 'progress_number', 'report_date', 'progress_percentage', 'attachment', 'notes')

class ScheduleInline(nested_admin.NestedTabularInline):
    model           = Schedule
    extra           = 0
    classes         = ['collapse',]
    fields          = ('boq_item', 'start_date', 'end_date', 'duration', 'duration_in_field', 'duration_for_client', 'duration_type', 'status', 'attachment', 'notes')

class BillOfQuantityInline(nested_admin.NestedTabularInline):
    model           = BillOfQuantity
    extra           = 0
    classes         = ['collapse',]
    fields          = ('project', 'document_name', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')
    inlines         = [ScheduleInline, ProgressReportInline, ]

class SubContractorOnProjectInline(nested_admin.NestedTabularInline):
    model   = SubContractorOnProject
    extra   = 0
    classes = ['collapse',]
    fields  = ('subcon', 'is_active', 'descriptions')

@admin.register(Project)
class ProjectAdmin(nested_admin.NestedModelAdmin):
    list_display    = ('project_code', 'client', 'team', 'start_date', 'end_date', 'project_status', 'progress_with_percent')
    list_filter     = ('project_status', 'client', 'team', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter), 'is_deleted')
    search_fields   = ('project_code', 'project_name', 'client__user__username', 'team__name', 'description')
    actions         = ['restore_selected',]
    date_hierarchy  = 'start_date'
    fieldsets = (
        (None, {
            "fields": (
                'project_code', 'project_name', 'location', 'client', 'team', 'start_date', 'end_date', 'project_status', 'progress', 'description'
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
    inlines         = [DocumentInline, DeflectInline, ErrorLogInline, WorkMethodInline, SubContractorOnProjectInline, BillOfQuantityInline]

    def progress_with_percent(self, obj):
        return f"{obj.progress} %"
    progress_with_percent.short_description = 'Progress'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('project_status', )
        
        return list(set(readonly_fields))
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected projects")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for document in obj.project_documents.all():
                if document.is_deleted:
                    document.is_deleted = False
                    document.deleted_at = None
                    document.deleted_by = None
                    document.save()
            for drawing in obj.project_drawings.all():
                if drawing.is_deleted:
                    drawing.is_deleted = False
                    drawing.deleted_at = None
                    drawing.deleted_by = None
                    drawing.save()
            for defect in obj.project_defect.all():
                if defect.is_deleted:
                    defect.is_deleted = False
                    defect.deleted_at = None
                    defect.deleted_by = None
                    defect.save()
            for error_log in obj.error_on_project.all():
                if error_log.is_deleted:
                    error_log.is_deleted = False
                    error_log.deleted_at = None
                    error_log.deleted_by = None
                    error_log.save()
            for work_method in obj.work_method_project.all():
                if work_method.is_deleted:
                    work_method.is_deleted = False
                    work_method.deleted_at = None
                    work_method.deleted_by = None
                    work_method.save()
            for boq in obj.project_boqs.all():
                if boq.is_deleted:
                    boq.is_deleted = False
                    boq.deleted_at = None
                    boq.deleted_by = None
                    boq.save()
            for payment_req in obj.project_payment_requests.all():
                if payment_req.is_deleted:
                    payment_req.is_deleted = False
                    payment_req.deleted_at = None
                    payment_req.deleted_by = None
                    payment_req.save()
            for expense in obj.project_expense.all():
                if expense.is_deleted:
                    expense.is_deleted = False
                    expense.deleted_at = None
                    expense.deleted_by = None
                    expense.save()
            for finance in obj.project_finance_data.all():
                if finance.is_deleted:
                    finance.is_deleted = False
                    finance.deleted_at = None
                    finance.deleted_by = None
                    finance.save()
            for petty_cash in obj.project_petty_cash.all():
                if petty_cash.is_deleted:
                    petty_cash.is_deleted = False
                    petty_cash.deleted_at = None
                    petty_cash.deleted_by = None
                    petty_cash.save()
            for material in obj.project_material.all():
                if material.is_deleted:
                    material.is_deleted = False
                    material.deleted_at = None
                    material.deleted_by = None
                    material.save()
            for tool in obj.project_tools.all():
                if tool.is_deleted:
                    tool.is_deleted = False
                    tool.deleted_at = None
                    tool.deleted_by = None
                    tool.save()
            for subcon in obj.project_subcon.all():
                if subcon.is_deleted:
                    subcon.is_deleted = False
                    subcon.deleted_at = None
                    subcon.deleted_by = None
                    subcon.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

# ──────────────── Schedule & WeeklyReport ────────────────

class SignatureOnScheduleInline(nested_admin.NestedTabularInline):
    model   = SignatureOnSchedule
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

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display    = ('boq_item', 'start_date', 'end_date', 'duration', 'duration_type', 'status')
    list_filter     = ('boq_item__project', 'duration_type', 'status', ('start_date', DateRangeFilter), ('end_date', DateRangeFilter), 'is_deleted')
    search_fields   = ('boq_item__description', 'notes')
    actions         = ['restore_selected',]
    fieldsets = (
        (None, {
            "fields": (
                'boq_item', 'start_date', 'end_date', 'duration', 'duration_in_field', 'duration_for_client', 'duration_type', 'status', 'attachment', 'notes'
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
    inlines         = [SignatureOnScheduleInline, ]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected schedules")
    def restore_selected(self, request, queryset):
        restored_count = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.is_deleted  = False
                obj.deleted_at  = None
                obj.deleted_by  = None
                obj.save()
                restored_count += 1
            for signature in obj.schedule_signature.all():
                if signature.is_deleted:
                    signature.is_deleted = False
                    signature.deleted_at = None
                    signature.deleted_by = None
                    signature.save()
        self.message_user(request,
            f"{restored_count} item berhasil di-restore.")

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'boq_item':
    #         kwargs["queryset"] = BillOfQuantityItemDetail.objects.select_related(
    #             'bill_of_quantity_subitem',
    #             'bill_of_quantity_subitem__bill_of_quantity_item',
    #         ).all()[:100]  # Limit jumlah data jika perlu
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display    = ('boq_item', 'progress_number', 'type', 'report_date', 'progress_with_percent')
    list_filter     = ('boq_item__project', 'progress_number', 'type', ('report_date', DateRangeFilter), ('progress_percentage', NumericRangeFilter), 'is_deleted')
    search_fields   = ('boq_item__description', 'notes')
    fieldsets = (
        (None, {
            "fields": (
                'boq_item', 'type', 'progress_number', 'report_date', 'progress_percentage', 'attachment', 'notes'
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
    actions         = ['restore_selected',]

    def progress_with_percent(self, obj):
        return f"{obj.progress_percentage} %"
    progress_with_percent.short_description = 'Progress'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Jika ada param filter is_deleted__exact di URL (True atau False),
        # kembalikan semua dulu, nanti list_filter yang akan nge-filter.
        if 'is_deleted__exact' in request.GET:
            return qs
        # Tanpa param, otomatis filter hanya yang is_deleted=False
        return qs.filter(is_deleted=False)
    
    @admin.action(description="Restore selected progress reports")
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

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'boq_item':
    #         kwargs["queryset"] = BillOfQuantityItemDetail.objects.select_related(
    #             'bill_of_quantity_subitem',
    #             'bill_of_quantity_subitem__bill_of_quantity_item',
    #         ).all()[:100]  # Limit jumlah data jika perlu
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)