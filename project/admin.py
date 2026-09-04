import calendar
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Max, OuterRef, Prefetch, Q, Subquery
from django.http import Http404
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from team.models import SubContractorOnProject
from finance.models import BillOfQuantity
from .models import *
from .forms import *
from .presentation import (
    build_project_showcase,
    build_showcase_summary,
)
from unfold.contrib.filters.admin import RangeDateFilter, RangeNumericFilter
from django.utils.safestring import mark_safe
from core.admin_mixins import ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin
from unfold.admin import ModelAdmin, TabularInline


# ──────────────── Document & Versions ────────────────

class DocumentVersionInline(TabularInline):
    tab = True
    model           = DocumentVersion
    extra           = 0
    classes         = ['collapse']
    fields          = ('title', 'document_number', 'document_file', 'status', 'notes', 'comment', 
                       'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = (
        'status', 'updated_by', 'updated_at', 'created_by', 'created_at',
    )

class SignatureOnDocumentInline(TabularInline):
    tab = True
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
class DocumentAdmin(
    ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin, ModelAdmin
):
    change_list_template = 'admin/project/document/change_list.html'
    approval_workflow_type = 'document'
    approval_required_role = 'pm,sm,ceo'
    autocomplete_fields = ('project', 'document_type')
    admin_select_related = ('project', 'document_type')
    list_display    = ('project', 'document_name', 'document_type', 'status', 'issue_date', 'due_date')
    list_filter     = ('project', 'document_type', 'status', ('issue_date', RangeDateFilter), ('due_date', RangeDateFilter), 'approval_required', 'approval_level', 'is_deleted')
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

    def get_urls(self):
        custom_urls = [
            path(
                'explorer/',
                self.admin_site.admin_view(self.document_explorer_view),
                name='project_document_explorer',
            ),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        if request.GET.get('view') == 'list':
            request.GET = request.GET.copy()
            request.GET.pop('view', None)
            extra_context = {
                **(extra_context or {}),
                'document_explorer_url': reverse(
                    'admin:project_document_explorer'
                ),
            }
            return super().changelist_view(
                request,
                extra_context=extra_context,
            )
        return self.document_explorer_view(request)

    def _explorer_url(self, request, **changes):
        parameters = {
            key: value
            for key, value in request.GET.items()
            if key != 'view'
        }
        for key, value in changes.items():
            if value in (None, ''):
                parameters.pop(key, None)
            else:
                parameters[key] = str(value)
        query = urlencode(parameters)
        base_url = reverse('admin:project_document_explorer')
        return f'{base_url}?{query}' if query else base_url

    @staticmethod
    def _document_file_icon(filename):
        extension = Path(filename or '').suffix.lower()
        if extension == '.pdf':
            return 'picture_as_pdf'
        if extension in {'.xls', '.xlsx', '.csv'}:
            return 'table_view'
        if extension in {'.doc', '.docx', '.odt', '.rtf'}:
            return 'description'
        if extension in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            return 'image'
        if extension in {'.dwg', '.dxf'}:
            return 'architecture'
        if extension in {'.zip', '.rar', '.7z'}:
            return 'folder_zip'
        return 'draft'

    def _document_cards(self, queryset, request):
        versions = DocumentVersion.objects.order_by(
            '-updated_at',
            '-created_at',
        )
        queryset = (
            queryset.select_related('project', 'document_type')
            .prefetch_related(
                Prefetch(
                    'versions',
                    queryset=versions,
                    to_attr='explorer_versions',
                )
            )
            .order_by('document_name', '-updated_at')
            .distinct()
        )
        paginator = Paginator(queryset, 36)
        page = paginator.get_page(request.GET.get('page'))
        cards = []
        for document in page.object_list:
            latest_version = (
                document.explorer_versions[0]
                if document.explorer_versions
                else None
            )
            file_name = ''
            file_url = ''
            if latest_version and latest_version.document_file:
                file_name = Path(
                    latest_version.document_file.name
                ).name
                try:
                    file_url = latest_version.document_file.url
                except (OSError, ValueError):
                    file_url = ''
            cards.append(
                {
                    'document': document,
                    'latest_version': latest_version,
                    'version_count': len(document.explorer_versions),
                    'file_name': file_name,
                    'file_url': file_url,
                    'file_icon': self._document_file_icon(file_name),
                    'change_url': reverse(
                        'admin:project_document_change',
                        args=(document.pk,),
                    ),
                }
            )
        return cards, page

    def document_explorer_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        scoped_queryset = self.get_queryset(request)
        query = (request.GET.get('q') or '').strip()
        project_id = request.GET.get('project')
        document_type_id = request.GET.get('document_type')
        status = request.GET.get('status')
        group_by = request.GET.get('group_by', 'project')
        if group_by not in {'project', 'type'}:
            group_by = 'project'

        selected_project = None
        if project_id:
            selected_project = Project.objects.filter(pk=project_id).first()
            if (
                selected_project is None
                or not scoped_queryset.filter(
                    project_id=selected_project.pk
                ).exists()
            ):
                raise Http404('Folder project tidak ditemukan.')

        selected_type = None
        if document_type_id:
            selected_type = DocumentType.objects.filter(
                pk=document_type_id
            ).first()
            if (
                selected_type is None
                or not scoped_queryset.filter(
                    document_type_id=selected_type.pk
                ).exists()
            ):
                raise Http404('Folder tipe dokumen tidak ditemukan.')

        queryset = scoped_queryset
        if query:
            queryset = queryset.filter(
                Q(document_name__icontains=query)
                | Q(project__project_name__icontains=query)
                | Q(project__project_code__icontains=query)
                | Q(document_type__name__icontains=query)
                | Q(versions__title__icontains=query)
                | Q(versions__document_number__icontains=query)
            )
        if selected_project:
            queryset = queryset.filter(project=selected_project)
        if selected_type:
            queryset = queryset.filter(document_type=selected_type)
        valid_statuses = {choice for choice, _ in DocumentStatus.choices}
        if status in valid_statuses:
            queryset = queryset.filter(status=status)
        else:
            status = ''

        show_files = (
            request.GET.get('show') == 'files'
            or bool(query)
            or bool(selected_project and selected_type)
        )
        folders = []
        if not show_files:
            group_projects = (
                (not selected_project and group_by == 'project')
                or bool(selected_type and not selected_project)
            )
            if group_projects:
                groups = (
                    queryset.values(
                        'project_id',
                        'project__project_name',
                        'project__project_code',
                    )
                    .annotate(
                        document_count=Count('pk', distinct=True),
                        type_count=Count(
                            'document_type_id',
                            distinct=True,
                        ),
                        latest_update=Max('updated_at'),
                    )
                    .order_by(
                        'project__project_code',
                        'project__project_name',
                    )
                )
                folders = [
                    {
                        'name': group['project__project_name'],
                        'code': group['project__project_code'],
                        'count': group['document_count'],
                        'secondary_count': group['type_count'],
                        'secondary_label': 'jenis',
                        'latest_update': group['latest_update'],
                        'url': self._explorer_url(
                            request,
                            project=group['project_id'],
                            show=None,
                            page=None,
                        ),
                    }
                    for group in groups
                ]
            else:
                groups = (
                    queryset.values(
                        'document_type_id',
                        'document_type__name',
                    )
                    .annotate(
                        document_count=Count('pk', distinct=True),
                        project_count=Count('project_id', distinct=True),
                        latest_update=Max('updated_at'),
                    )
                    .order_by('document_type__name')
                )
                folders = [
                    {
                        'name': group['document_type__name'],
                        'code': 'DOCUMENT TYPE',
                        'count': group['document_count'],
                        'secondary_count': group['project_count'],
                        'secondary_label': 'project',
                        'latest_update': group['latest_update'],
                        'url': self._explorer_url(
                            request,
                            document_type=group['document_type_id'],
                            show=None,
                            page=None,
                        ),
                    }
                    for group in groups
                ]

        document_cards = []
        page = None
        previous_page_url = ''
        next_page_url = ''
        if show_files:
            document_cards, page = self._document_cards(
                queryset,
                request,
            )
            if page.has_previous():
                previous_page_url = self._explorer_url(
                    request,
                    page=page.previous_page_number(),
                )
            if page.has_next():
                next_page_url = self._explorer_url(
                    request,
                    page=page.next_page_number(),
                )

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Document Explorer',
            'folders': folders,
            'document_cards': document_cards,
            'page_obj': page,
            'previous_page_url': previous_page_url,
            'next_page_url': next_page_url,
            'query': query,
            'selected_project': selected_project,
            'selected_type': selected_type,
            'selected_status': status,
            'status_choices': DocumentStatus.choices,
            'group_by': group_by,
            'show_files': show_files,
            'explorer_url': reverse('admin:project_document_explorer'),
            'table_url': (
                f"{reverse('admin:project_document_changelist')}?view=list"
            ),
            'add_url': reverse('admin:project_document_add'),
            'root_url': self._explorer_url(
                request,
                project=None,
                document_type=None,
                show=None,
                page=None,
                q=None,
                status=None,
            ),
            'show_all_files_url': self._explorer_url(
                request,
                show='files',
                page=None,
            ),
            'group_project_url': self._explorer_url(
                request,
                group_by='project',
                project=None,
                document_type=None,
                show=None,
                page=None,
                q=None,
            ),
            'group_type_url': self._explorer_url(
                request,
                group_by='type',
                project=None,
                document_type=None,
                show=None,
                page=None,
                q=None,
            ),
            'has_add_permission': self.has_add_permission(request),
        }
        return render(
            request,
            'admin/project/document/explorer.html',
            context,
        )

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

class DrawingVersionInline(TabularInline):
    tab = True
    model           = DrawingVersion
    extra           = 0
    classes         = ['collapse',]
    fields          = ('title', 'document_number', 'drawing_file', 'status', 'notes', 'comment', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = (
        'status', 'updated_by', 'updated_at', 'created_by', 'created_at',
    )

class SignatureOnDrawingInline(TabularInline):
    tab = True
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
class DrawingAdmin(
    ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin, ModelAdmin
):
    approval_workflow_type = 'drawing'
    approval_required_role = 'architect,pm,ceo'
    autocomplete_fields = ('project', 'drawing_type')
    admin_select_related = ('project', 'drawing_type')
    list_display    = ('project', 'document_name', 'drawing_type', 'status', 'issue_date', 'due_date')
    list_filter     = ('project', 'drawing_type', 'status', ('issue_date', RangeDateFilter), ('due_date', RangeDateFilter), 'is_deleted')
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

class DefectDetailInline(TabularInline):
    tab = True
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
    

class SignatureOnDeflectInline(TabularInline):
    tab = True
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
class DefectAdmin(SoftDeleteAdminMixin, ModelAdmin):
    autocomplete_fields = ('project',)
    admin_select_related = ('project',)
    list_display    = ('project', 'work_title', 'location', 'is_approved', 'approved_at')
    list_filter     = ('project', 'is_approved', ('approved_at', RangeDateFilter), 'is_deleted')
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

class ErrorLogDetailInline(TabularInline):
    tab = True
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

class SignatureOnErrorLogInline(TabularInline):
    tab = True
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
class ErrorLogAdmin(SoftDeleteAdminMixin, ModelAdmin):
    autocomplete_fields = ('project', 'work_type')
    admin_select_related = ('project', 'work_type')
    list_display    = ('project', 'work_type', 'periode_start', 'periode_end')
    list_filter     = ('project', 'work_type', ('periode_start', RangeDateFilter), ('periode_end', RangeDateFilter), 'is_deleted')
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

class SignatureOnWorkMethodInline(TabularInline):
    tab = True
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
class WorkMethodAdmin(SoftDeleteAdminMixin, ModelAdmin):
    autocomplete_fields = ('project',)
    admin_select_related = ('project',)
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

class DocumentInline(TabularInline):
    tab = True
    model           = Document
    extra           = 0
    classes         = ['collapse',]
    fields          = ('document_name', 'document_type', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date')
    inlines         = [DocumentVersionInline, SignatureOnDocumentInline]

class DeflectInline(TabularInline):
    tab = True
    model   = Defect
    extra   = 0
    classes = ['collapse',]
    fields  = ('work_title', 'location', 'is_approved', 'approved_at')
    inlines = [DefectDetailInline, SignatureOnDeflectInline]

class ErrorLogInline(TabularInline):
    tab = True
    model   = ErrorLog
    extra   = 0
    classes = ['collapse',]
    fields  = ('document_number', 'work_type', 'periode_start', 'periode_end', 'notes')
    inlines = [ErrorLogDetailInline, SignatureOnErrorLogInline]

class WorkMethodInline(TabularInline):
    tab = True
    model   = WorkMethod
    extra   = 0
    classes = ['collapse',]
    fields  = ('work_title', 'document_number', 'file', 'notes')
    inlines = [SignatureOnWorkMethodInline,]

class ProgressReportInline(TabularInline):
    tab = True
    model           = ProgressReport
    extra           = 0
    classes         = ['collapse',]
    fields          = ('boq_item', 'type', 'progress_number', 'report_date', 'progress_percentage', 'attachment', 'notes')

class ScheduleInline(TabularInline):
    tab = True
    model           = Schedule
    extra           = 0
    classes         = ['collapse',]
    fields          = ('boq_item', 'start_date', 'end_date', 'duration', 'duration_in_field', 'duration_for_client', 'duration_type', 'status', 'attachment', 'notes')

class BillOfQuantityInline(TabularInline):
    tab = True
    model           = BillOfQuantity
    extra           = 0
    classes         = ['collapse',]
    fields          = ('project', 'document_name', 'status', 'approval_required', 'approval_level', 'issue_date', 'due_date', 'updated_by', 'updated_at', 'created_by', 'created_at')
    readonly_fields = ('updated_by', 'updated_at', 'created_by', 'created_at')
    inlines         = [ScheduleInline, ProgressReportInline, ]

class SubContractorOnProjectInline(TabularInline):
    tab = True
    model   = SubContractorOnProject
    extra   = 0
    classes = ['collapse',]
    fields  = ('subcon', 'is_active', 'descriptions')

@admin.register(Project)
class ProjectAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('client', 'team', 'location')
    autocomplete_fields = ('location', 'client', 'team')
    list_before_template = 'admin/project/project/showcase_list.html'
    change_form_outer_before_template = (
        'admin/project/project/showcase_detail.html'
    )
    list_display    = ('project_code', 'client', 'team', 'start_date', 'end_date', 'project_status', 'progress_with_percent')
    list_filter     = ('project_status', 'client', 'team', ('start_date', RangeDateFilter), ('end_date', RangeDateFilter), 'is_deleted')
    search_fields   = ('project_code', 'project_name', 'client__user__username', 'team__name', 'description')
    actions         = ['restore_selected',]
    date_hierarchy  = 'start_date'
    fieldsets = (
        ('PRESENTASI', {
            'description': (
                'Gunakan foto desain, render, atau blueprint berformat '
                'gambar untuk memperkuat tampilan showcase client.'
            ),
            'fields': ('presentation_image',),
        }),
        ('INFORMASI PROYEK', {
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
    readonly_fields = (
        'progress',
        'updated_by', 'updated_at', 'created_by', 'created_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
    # Detail berat dikelola di menu masing-masing; ini menjaga halaman proyek
    # tetap cepat meskipun data dokumen dan progress sudah besar.
    inlines = [SubContractorOnProjectInline]

    class Media:
        css = {
            'all': ('admin/css/project_showcase.css',),
        }

    def progress_with_percent(self, obj):
        progress = float(obj.progress or 0)
        return format_html(
            (
                '<div class="mmg-table-progress" '
                'aria-label="Progress {}%">'
                '<span class="mmg-table-progress__track">'
                '<i style="width: {}%"></i>'
                '</span>'
                '<strong>{}%</strong>'
                '</div>'
            ),
            f'{progress:.0f}',
            progress,
            f'{progress:.0f}',
        )
    progress_with_percent.short_description = 'Progress'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly_fields += ('project_status', )
        
        return list(set(readonly_fields))
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)

        latest_drawing = (
            DrawingVersion.all_objects
            .filter(
                drawing__project_id=OuterRef('pk'),
                drawing__is_deleted=False,
                is_deleted=False,
            )
            .exclude(drawing_file='')
            .order_by('-created_at')
        )
        latest_report = (
            ProgressReport.all_objects
            .filter(
                boq_item__project_id=OuterRef('pk'),
                boq_item__is_deleted=False,
                is_deleted=False,
            )
            .order_by('-report_date', '-progress_number', '-created_at')
        )
        closed_schedule_statuses = (
            ScheduleStatusType.COMPLETED,
            ScheduleStatusType.CANCELLED,
            ScheduleStatusType.CANCELLED_BY_CLIENT,
        )

        return qs.annotate(
            documents_total=Count(
                'project_documents',
                filter=Q(project_documents__is_deleted=False),
                distinct=True,
            ),
            documents_approved=Count(
                'project_documents',
                filter=Q(
                    project_documents__is_deleted=False,
                    project_documents__status__in=(
                        DocumentStatus.APPROVED,
                        DocumentStatus.FINALIZED,
                    ),
                ),
                distinct=True,
            ),
            drawings_total=Count(
                'project_drawings',
                filter=Q(project_drawings__is_deleted=False),
                distinct=True,
            ),
            drawings_approved=Count(
                'project_drawings',
                filter=Q(
                    project_drawings__is_deleted=False,
                    project_drawings__status__in=(
                        DocumentStatus.APPROVED,
                        DocumentStatus.FINALIZED,
                    ),
                ),
                distinct=True,
            ),
            open_defects=Count(
                'project_defect',
                filter=Q(
                    project_defect__is_deleted=False,
                    project_defect__is_approved=False,
                ),
                distinct=True,
            ),
            overdue_schedules=Count(
                'project_boqs__schedules_boq',
                filter=Q(
                    project_boqs__is_deleted=False,
                    project_boqs__schedules_boq__is_deleted=False,
                    project_boqs__schedules_boq__end_date__lt=(
                        timezone.localdate()
                    ),
                )
                & ~Q(
                    project_boqs__schedules_boq__status__in=(
                        closed_schedule_statuses
                    ),
                ),
                distinct=True,
            ),
            team_members_total=Count(
                'team__members',
                filter=Q(
                    team__members__is_deleted=False,
                    team__members__is_active=True,
                ),
                distinct=True,
            ),
            latest_drawing_file=Subquery(
                latest_drawing.values('drawing_file')[:1]
            ),
            latest_report_date=Subquery(
                latest_report.values('report_date')[:1]
            ),
        )

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        context = getattr(response, 'context_data', None)
        if not context or 'cl' not in context:
            return response

        change_list = context['cl']
        projects = list(change_list.result_list)
        context['project_showcase_cards'] = [
            build_project_showcase(project)
            for project in projects[:6]
        ]
        context['project_showcase_summary'] = build_showcase_summary(
            change_list.queryset
        )
        context['project_showcase_total_on_page'] = len(projects)
        return response

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url='',
        extra_context=None,
    ):
        response = super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context,
        )
        context = getattr(response, 'context_data', None)
        if context and context.get('original') is not None:
            context['project_showcase'] = build_project_showcase(
                context['original']
            )
        return response

    def get_urls(self):
        custom_urls = [
            path(
                '<path:object_id>/presentation/',
                self.admin_site.admin_view(self.presentation_view),
                name='project_project_presentation',
            ),
        ]
        return custom_urls + super().get_urls()

    def presentation_view(self, request, object_id):
        project = self.get_object(request, object_id)
        if project is None:
            raise Http404('Project tidak ditemukan.')
        if not self.has_view_permission(request, project):
            raise PermissionDenied

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': f'Presentasi · {project.project_name}',
            'project': project,
            'project_showcase': build_project_showcase(
                project,
                include_recent_documents=True,
            ),
        }
        return render(
            request,
            'admin/project/project/presentation.html',
            context,
        )
    
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

class SignatureOnScheduleInline(TabularInline):
    tab = True
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
class ScheduleAdmin(SoftDeleteAdminMixin, ModelAdmin):
    change_list_template = 'admin/project/schedule/change_list.html'
    autocomplete_fields = ('boq_item',)
    admin_select_related = ('boq_item', 'boq_item__project')
    list_display = (
        'schedule_name',
        'project_name',
        'date_window',
        'duration_label',
        'status',
    )
    list_display_links = ('schedule_name',)
    list_filter = (
        'boq_item__project',
        'duration_type',
        'status',
        ('start_date', RangeDateFilter),
        ('end_date', RangeDateFilter),
        'is_deleted',
    )
    search_fields = (
        'boq_item__document_name',
        'boq_item__project__project_code',
        'boq_item__project__project_name',
        'notes',
    )
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

    @admin.display(description='Schedule / BOQ', ordering='boq_item__document_name')
    def schedule_name(self, obj):
        notes = (obj.notes or '').strip()
        if len(notes) > 72:
            notes = f'{notes[:69]}…'
        return format_html(
            '<span class="mmg-list-primary">{}</span>'
            '<span class="mmg-list-secondary">{}</span>',
            obj.boq_item.document_name,
            notes or 'Tidak ada catatan',
        )

    @admin.display(
        description='Project',
        ordering='boq_item__project__project_name',
    )
    def project_name(self, obj):
        project = obj.boq_item.project
        return format_html(
            '<span class="mmg-list-primary">{}</span>'
            '<span class="mmg-list-secondary">{}</span>',
            project.project_name,
            project.project_code,
        )

    @admin.display(description='Periode', ordering='start_date')
    def date_window(self, obj):
        return format_html(
            '<span class="mmg-date-window">'
            '<span><i></i>{}</span>'
            '<span><i></i>{}</span>'
            '</span>',
            obj.start_date.strftime('%d %b %Y'),
            obj.end_date.strftime('%d %b %Y'),
        )

    @admin.display(description='Durasi', ordering='duration')
    def duration_label(self, obj):
        duration = (
            int(obj.duration)
            if float(obj.duration).is_integer()
            else obj.duration
        )
        return format_html(
            '<span class="mmg-duration-chip">{} {}</span>',
            duration,
            obj.get_duration_type_display().lower(),
        )

    def get_urls(self):
        custom_urls = [
            path(
                'calendar/',
                self.admin_site.admin_view(self.calendar_view),
                name='project_schedule_calendar',
            ),
            path(
                'list/',
                self.admin_site.admin_view(self.list_view),
                name='project_schedule_list',
            ),
        ]
        return custom_urls + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return self.calendar_view(request)

    def list_view(self, request):
        extra_context = {
            'calendar_url': reverse('admin:project_schedule_calendar'),
        }
        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    @staticmethod
    def _month_start(raw_month):
        if raw_month:
            try:
                return date.fromisoformat(f'{raw_month}-01')
            except ValueError:
                pass
        return timezone.localdate().replace(day=1)

    @staticmethod
    def _month_value(month):
        return month.strftime('%Y-%m')

    def _calendar_url(self, month, project_id='', status=''):
        parameters = {'month': self._month_value(month)}
        if project_id:
            parameters['project'] = str(project_id)
        if status:
            parameters['status'] = status
        return (
            f"{reverse('admin:project_schedule_calendar')}?"
            f'{urlencode(parameters)}'
        )

    def calendar_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        month_start = self._month_start(request.GET.get('month'))
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        previous_month = (month_start - timedelta(days=1)).replace(day=1)
        month_end = next_month - timedelta(days=1)

        queryset = self.get_queryset(request).select_related(
            'boq_item',
            'boq_item__project',
        )
        project_ids = queryset.values_list(
            'boq_item__project_id',
            flat=True,
        ).distinct()
        projects = Project.objects.filter(
            pk__in=project_ids,
            is_deleted=False,
        ).order_by('project_code', 'project_name')

        selected_project = None
        project_id = request.GET.get('project', '')
        if project_id:
            try:
                selected_project = projects.filter(pk=project_id).first()
            except (ValidationError, ValueError):
                selected_project = None
            if selected_project:
                queryset = queryset.filter(
                    boq_item__project=selected_project
                )
            else:
                project_id = ''

        valid_statuses = {
            value for value, _label in ScheduleStatusType.choices
        }
        selected_status = request.GET.get('status', '')
        if selected_status in valid_statuses:
            queryset = queryset.filter(status=selected_status)
        else:
            selected_status = ''

        schedules = list(
            queryset.filter(
                start_date__lte=month_end,
                end_date__gte=month_start,
            ).order_by(
                'start_date',
                'end_date',
                'boq_item__project__project_code',
                'boq_item__document_name',
            )
        )

        month_calendar = calendar.Calendar(firstweekday=0)
        weeks = month_calendar.monthdatescalendar(
            month_start.year,
            month_start.month,
        )
        today = timezone.localdate()
        calendar_weeks = []
        for week in weeks:
            week_start = week[0]
            week_end = week[-1]
            segments = []
            for schedule in schedules:
                if (
                    schedule.start_date > week_end
                    or schedule.end_date < week_start
                ):
                    continue
                segment_start = max(schedule.start_date, week_start)
                segment_end = min(schedule.end_date, week_end)
                start_column = (segment_start - week_start).days + 1
                segments.append(
                    {
                        'schedule': schedule,
                        'change_url': reverse(
                            'admin:project_schedule_change',
                            args=(schedule.pk,),
                        ),
                        'tone': self.get_status_tone(schedule.status),
                        'start_column': start_column,
                        'span': (segment_end - segment_start).days + 1,
                        'end_column': (
                            start_column
                            + (segment_end - segment_start).days
                        ),
                        'continues_before': (
                            schedule.start_date < week_start
                        ),
                        'continues_after': schedule.end_date > week_end,
                    }
                )

            segments.sort(
                key=lambda segment: (
                    segment['start_column'],
                    -segment['span'],
                    segment['schedule'].start_date,
                    segment['schedule'].boq_item.project.project_code,
                    segment['schedule'].boq_item.document_name,
                )
            )
            lane_ends = []
            for segment in segments:
                lane_index = next(
                    (
                        index
                        for index, lane_end in enumerate(lane_ends)
                        if lane_end < segment['start_column']
                    ),
                    None,
                )
                if lane_index is None:
                    lane_index = len(lane_ends)
                    lane_ends.append(segment['end_column'])
                else:
                    lane_ends[lane_index] = segment['end_column']
                segment['row'] = lane_index + 2

            lane_count = max(len(lane_ends), 1)
            calendar_weeks.append(
                {
                    'days': [
                        {
                            'date': day,
                            'column': column,
                            'in_month': (
                                day.month == month_start.month
                            ),
                            'is_today': day == today,
                        }
                        for column, day in enumerate(week, start=1)
                    ],
                    'segments': segments,
                    'lane_count': lane_count,
                    'row_count': lane_count + 1,
                }
            )

        completed_statuses = {
            ScheduleStatusType.COMPLETED,
        }
        closed_statuses = {
            *completed_statuses,
            ScheduleStatusType.CANCELLED,
            ScheduleStatusType.CANCELLED_BY_CLIENT,
        }
        summary = {
            'total': len(schedules),
            'active': sum(
                schedule.status not in closed_statuses
                for schedule in schedules
            ),
            'completed': sum(
                schedule.status in completed_statuses
                for schedule in schedules
            ),
            'overdue': sum(
                schedule.end_date < today
                and schedule.status not in closed_statuses
                for schedule in schedules
            ),
        }

        # Daftar datar untuk tampilan agenda. Grid tujuh kolom tidak muat di
        # layar ponsel, jadi template menampilkan agenda ini sebagai gantinya.
        agenda = [
            {
                'schedule': schedule,
                'change_url': reverse(
                    'admin:project_schedule_change',
                    args=(schedule.pk,),
                ),
                'tone': self.get_status_tone(schedule.status),
                'starts_before': schedule.start_date < month_start,
                'ends_after': schedule.end_date > month_end,
            }
            for schedule in schedules
        ]

        month_names = (
            '',
            'Januari',
            'Februari',
            'Maret',
            'April',
            'Mei',
            'Juni',
            'Juli',
            'Agustus',
            'September',
            'Oktober',
            'November',
            'Desember',
        )
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Schedule Calendar',
            'calendar_weeks': calendar_weeks,
            'agenda': agenda,
            'weekday_labels': (
                'Sen',
                'Sel',
                'Rab',
                'Kam',
                'Jum',
                'Sab',
                'Min',
            ),
            'month_label': (
                f'{month_names[month_start.month]} {month_start.year}'
            ),
            'month_value': self._month_value(month_start),
            'projects': projects,
            'selected_project': selected_project,
            'selected_project_id': project_id,
            'status_choices': ScheduleStatusType.choices,
            'selected_status': selected_status,
            'summary': summary,
            'previous_url': self._calendar_url(
                previous_month,
                project_id,
                selected_status,
            ),
            'next_url': self._calendar_url(
                next_month,
                project_id,
                selected_status,
            ),
            'today_url': self._calendar_url(
                today.replace(day=1),
                project_id,
                selected_status,
            ),
            'calendar_url': reverse('admin:project_schedule_calendar'),
            'changelist_url': reverse(
                'admin:project_schedule_changelist'
            ),
            'list_url': (
                reverse('admin:project_schedule_list')
            ),
            'add_url': reverse('admin:project_schedule_add'),
            'has_add_permission': self.has_add_permission(request),
        }
        return render(
            request,
            'admin/project/schedule/calendar.html',
            context,
        )
    
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
class ProgressReportAdmin(SoftDeleteAdminMixin, ModelAdmin):
    list_before_template = 'admin/project/progressreport/overview.html'
    autocomplete_fields = ('boq_item',)
    admin_select_related = ('boq_item', 'boq_item__project')
    list_display    = ('boq_item', 'progress_number', 'type', 'report_date', 'progress_with_percent')
    list_filter     = ('boq_item__project', 'progress_number', 'type', ('report_date', RangeDateFilter), ('progress_percentage', RangeNumericFilter), 'is_deleted')
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

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        if not hasattr(response, 'context_data'):
            return response
        changelist = response.context_data.get('cl')
        if changelist is None:
            return response

        queryset = changelist.queryset
        project_ids = queryset.values_list(
            'boq_item__project_id',
            flat=True,
        ).distinct()
        latest_report_dates = {
            row['boq_item__project_id']: row['last_report']
            for row in queryset.values(
                'boq_item__project_id'
            ).annotate(last_report=Max('report_date'))
        }
        today = timezone.localdate()
        projects = []
        for project in Project.objects.filter(
            pk__in=project_ids,
            is_deleted=False,
        ).order_by('project_code'):
            actual = float(project.progress or 0)
            if today <= project.start_date:
                planned = 0
            elif project.end_date and today >= project.end_date:
                planned = 100
            elif project.end_date:
                total_days = max(
                    (project.end_date - project.start_date).days,
                    1,
                )
                elapsed_days = (
                    today - project.start_date
                ).days
                planned = min(
                    max(elapsed_days / total_days * 100, 0),
                    100,
                )
            else:
                planned = None
            variance = actual - planned if planned is not None else None
            if variance is None:
                tone = 'neutral'
            elif variance < -10:
                tone = 'danger'
            elif variance < 0:
                tone = 'warning'
            else:
                tone = 'success'
            projects.append(
                {
                    'project': project,
                    'actual': round(actual, 1),
                    'planned': (
                        round(planned, 1)
                        if planned is not None
                        else None
                    ),
                    'variance': (
                        round(variance, 1)
                        if variance is not None
                        else None
                    ),
                    'tone': tone,
                    'last_report': latest_report_dates.get(project.pk),
                }
            )
        projects.sort(
            key=lambda item: (
                item['variance'] is None,
                item['variance'] if item['variance'] is not None else 0,
            )
        )
        response.context_data['progress_overview'] = {
            'projects': projects[:8],
            'today': today,
        }
        return response

    def progress_with_percent(self, obj):
        percentage = min(max(float(obj.progress_percentage), 0), 100)
        return format_html(
            '<span class="mmg-progress-cell">'
            '<span><strong>{}%</strong><small>Report #{}</small></span>'
            '<span><i style="width: {}%"></i></span></span>',
            round(percentage, 1),
            obj.progress_number,
            percentage,
        )
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
