import calendar
from datetime import date, timedelta

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import *
from unfold.contrib.filters.admin import RangeDateFilter
from django.utils.safestring import mark_safe
import mapwidgets
from .forms import *
from core.admin_mixins import ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin
from team.attendance_exports import (
    attendance_export_filename,
    build_attendance_excel,
    build_attendance_pdf,
)
from team.services import validate_attendance_location
from unfold.admin import ModelAdmin, TabularInline


MONTH_NAMES = (
    '',
    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember',
)

WEEKDAY_NAMES = (
    'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu',
)

WEEKDAY_SHORT = ('Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min')


# ──────────────── Team & Members ────────────────

class TeamMemberInline(TabularInline):
    tab = True
    model           = TeamMember
    extra           = 0
    classes         = ['collapse']
    fields          = ('user', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

@admin.register(Team)
class TeamAdmin(SoftDeleteAdminMixin, ModelAdmin):
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
# class TeamMemberAdmin(ModelAdmin):
#     list_display   = ('user', 'team', 'is_active', 'timestamp')
#     list_filter    = ('team', 'is_active')
#     search_fields  = ('user__full_name', 'team__name')
#     readonly_fields = ('id', 'timestamp')

# ──────────────── Profile ────────────────

class TeamMemberInline(TabularInline):
    tab = True
    model           = TeamMember
    extra           = 0
    classes         = ['collapse']
    fields          = ('team', 'is_active', 'timestamp')
    readonly_fields = ('timestamp',)

class SignatureInline(TabularInline):
    tab = True
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

class InitialInline(TabularInline):
    tab = True
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
class AttendanceModelAdmin(SoftDeleteAdminMixin, ModelAdmin):
    change_list_template = "admin/team/attendance/change_list.html"
    list_before_template = 'admin/team/attendance/heatmap.html'
    admin_select_related = (
        'user',
        'user__user',
        'user__location',
        'work_policy',
        'work_policy__office_location',
    )
    autocomplete_fields = ('user', 'work_policy')
    form = AttendanceAdminForm
    list_display = (
        'user', 'date', 'work_mode', 'check_in', 'check_out', 'status',
        'worked_minutes', 'overtime_minutes',
    )
    list_filter = (
        'user', 'date', 'work_mode', 'status', 'work_policy', 'is_deleted',
    )
    search_fields   = ('user__full_name', 'status')
    actions = ['restore_selected']

    class Media:
        css = {
            'all': ('admin/css/admin_insights.css',),
        }

    def _attendance_heatmap(self, request):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        month_end = date(
            today.year,
            today.month,
            calendar.monthrange(today.year, today.month)[1],
        )
        # Role client bukan staff absensi, jadi tidak pernah masuk heatmap
        # baik sebagai baris maupun sebagai penonton.
        if request.user.is_superuser:
            profiles = list(
                Profile.objects.filter(
                    is_active=True,
                    is_deleted=False,
                ).exclude(
                    role=RoleType.CLIENT,
                ).select_related(
                    'user',
                    'work_policy',
                ).order_by('full_name')[:12]
            )
        else:
            profiles = list(
                Profile.objects.filter(
                    user=request.user,
                ).exclude(
                    role=RoleType.CLIENT,
                ).select_related(
                    'user',
                    'work_policy',
                )[:1]
            )

        if not profiles:
            return None

        records = {
            (attendance.user_id, attendance.date): attendance
            for attendance in self.get_queryset(request).filter(
                user__in=profiles,
                date__range=(month_start, month_end),
            ).select_related('user', 'work_policy')
        }
        holidays = {
            holiday.date: holiday.name
            for holiday in Holiday.objects.filter(
                date__range=(month_start, month_end),
                is_deleted=False,
            )
        }
        days = [
            month_start.replace(day=day_number)
            for day_number in range(1, month_end.day + 1)
        ]
        rows = []
        late_statuses = {
            AttendanceStatus.LATE,
            AttendanceStatus.LATE_EARLY_LEAVE,
        }
        present_statuses = {
            AttendanceStatus.ONTIME,
            AttendanceStatus.LATE,
            AttendanceStatus.EARLY_LEAVE,
            AttendanceStatus.LATE_EARLY_LEAVE,
            AttendanceStatus.OVERTIME,
        }
        for profile in profiles:
            workdays = set(
                (
                    profile.work_policy.workdays
                    if profile.work_policy_id
                    else [0, 1, 2, 3, 4]
                )
                or [0, 1, 2, 3, 4]
            )
            cells = []
            counts = {
                'present': 0,
                'late': 0,
                'absent': 0,
                'wfh': 0,
            }
            for day in days:
                attendance = records.get((profile.pk, day))
                title = day.strftime('%d %b %Y')
                if attendance:
                    status = attendance.status
                    if attendance.work_mode == AttendanceWorkMode.WFH:
                        tone = 'wfh'
                        counts['wfh'] += 1
                    elif status in late_statuses:
                        tone = 'late'
                    elif status == AttendanceStatus.ABSENT:
                        tone = 'absent'
                    elif status == AttendanceStatus.LEAVE:
                        tone = 'leave'
                    elif status == AttendanceStatus.HOLYDAY:
                        tone = 'holiday'
                    else:
                        tone = 'present'
                    if status in present_statuses:
                        counts['present'] += 1
                    if status in late_statuses:
                        counts['late'] += 1
                    if status == AttendanceStatus.ABSENT:
                        counts['absent'] += 1
                    title = (
                        f'{title} · {attendance.get_status_display()}'
                        f' · {attendance.get_work_mode_display()}'
                    )
                elif day > today:
                    tone = 'future'
                elif day < profile.join_date:
                    tone = 'off'
                elif day in holidays:
                    tone = 'holiday'
                    title = f'{title} · {holidays[day]}'
                elif day.weekday() not in workdays:
                    tone = 'off'
                else:
                    tone = 'absent'
                    counts['absent'] += 1
                cells.append(
                    {
                        'date': day,
                        'tone': tone,
                        'title': title,
                    }
                )
            rows.append(
                {
                    'profile': profile,
                    'cells': cells,
                    **counts,
                }
            )

        return {
            'label': f'{MONTH_NAMES[today.month]} {today.year}',
            'days': days,
            'rows': rows,
        }

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(
            request,
            extra_context=extra_context,
        )
        if hasattr(response, 'context_data'):
            response.context_data['attendance_heatmap'] = (
                self._attendance_heatmap(request)
            )
        return response

    def get_urls(self):
        custom_urls = [
            path(
                'report/',
                self.admin_site.admin_view(
                    self.attendance_report_view
                ),
                name='team_attendance_report',
            ),
            path(
                'export/excel/',
                self.admin_site.admin_view(
                    self.export_filtered_excel
                ),
                name='team_attendance_export_excel',
            ),
            path(
                'export/pdf/',
                self.admin_site.admin_view(
                    self.export_filtered_pdf
                ),
                name='team_attendance_export_pdf',
            ),
        ]
        return custom_urls + super().get_urls()

    def _report_queryset(self, request, date_from, date_to):
        """Batasi periode sekaligus terapkan scope akses Attendance admin."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        return (
            self.get_queryset(request)
            .filter(date__range=(date_from, date_to))
            .select_related(
                'user',
                'user__user',
                'work_policy',
            )
            .order_by('date', 'user__full_name', 'user__user__username')
        )

    def _export_response(
        self,
        queryset,
        export_format,
        date_from=None,
        date_to=None,
    ):
        records = list(
            queryset.select_related(
                'user',
                'user__user',
                'work_policy',
            )
        )
        if export_format == 'xlsx':
            content = build_attendance_excel(
                records,
                date_from=date_from,
                date_to=date_to,
            )
            content_type = (
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet'
            )
        else:
            content = build_attendance_pdf(
                records,
                date_from=date_from,
                date_to=date_to,
            )
            content_type = 'application/pdf'

        filename = attendance_export_filename(
            records,
            export_format,
            date_from=date_from,
            date_to=date_to,
        )
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"'
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    def attendance_report_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        today = timezone.localdate()
        initial = {
            'date_from': today.replace(day=1),
            'date_to': today,
            'output_format': (
                request.GET.get('format')
                if request.GET.get('format') in {'xlsx', 'pdf'}
                else 'xlsx'
            ),
        }
        form = AttendanceReportForm(
            request.POST or None,
            initial=initial,
        )
        if request.method == 'POST' and form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            export_format = form.cleaned_data['output_format']
            return self._export_response(
                self._report_queryset(
                    request,
                    date_from,
                    date_to,
                ),
                export_format,
                date_from=date_from,
                date_to=date_to,
            )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Laporan Attendance',
            'opts': self.model._meta,
            'form': form,
            'scope_label': (
                'Seluruh staff'
                if request.user.is_superuser
                else 'Data attendance Anda sendiri'
            ),
            'changelist_url': reverse(
                'admin:team_attendance_changelist'
            ),
        }
        return TemplateResponse(
            request,
            'admin/team/attendance/report.html',
            context,
        )

    def _legacy_report_redirect(self, request, export_format):
        if not self.has_view_permission(request):
            raise PermissionDenied
        report_url = reverse('admin:team_attendance_report')
        return HttpResponseRedirect(
            f'{report_url}?format={export_format}'
        )

    def export_filtered_excel(self, request):
        return self._legacy_report_redirect(request, 'xlsx')

    def export_filtered_pdf(self, request):
        return self._legacy_report_redirect(request, 'pdf')

    def get_autocomplete_fields(self, request):
        """
        Autocomplete relasi membutuhkan permission terhadap model tujuan.

        Staff tetap harus dapat memilih seluruh work policy aktif ketika
        sedang dinas atau bekerja di lokasi proyek, tanpa harus diberi
        permission untuk membuka/mengubah konfigurasi WorkPolicy.
        """
        if request.user.is_superuser:
            return self.autocomplete_fields
        return ()

    fieldsets = (
        ('RINGKASAN', {
            "fields": (
                'user', 'date', 'work_policy', 'work_mode', 'status',
                'status_override', 'status_override_reason',
                'worked_minutes', 'overtime_minutes',
            ),
        }),
        ('CHECK IN/DATANG', {
            "fields": (
                ('photo_check_in', 'display_check_in_photo'),
                'check_in',
                'check_in_location_label',
                'check_in_location',
                'check_in_accuracy_meters',
                'check_in_distance_meters',
            ),
        }),
        ('CHECK OUT/PULANG', {
            "fields": (
                ('photo_check_out', 'display_check_out_photo'),
                'check_out',
                'check_out_location_label',
                'check_out_location',
                'check_out_accuracy_meters',
                'check_out_distance_meters',
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
        'status', 'worked_minutes', 'overtime_minutes',
        'check_in_accuracy_meters', 'check_out_accuracy_meters',
        'check_in_distance_meters', 'check_out_distance_meters',
        'display_check_in_photo', 'display_check_out_photo',
        'updated_by', 'updated_at', 'created_by', 'created_at',
        'is_deleted', 'deleted_at', 'deleted_by',
    )
   
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

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return self.fieldsets

        if obj is None:
            return (
                ('CHECK-IN HARI INI', {
                    'description': (
                        'Pilih work policy lalu ambil foto langsung dari '
                        'kamera. User, tanggal, waktu, lokasi, dan status '
                        'akan diisi otomatis.'
                    ),
                    'fields': (
                        'work_policy',
                        'work_mode',
                        'photo_check_in',
                        'check_in_location',
                        'check_in_gps_accuracy',
                    ),
                }),
            )

        summary_fields = (
            'user',
            'date',
            'status',
            'work_policy',
            'work_mode',
            'check_in',
            'check_in_location_label',
            'check_in_accuracy_meters',
            'check_in_distance_meters',
            'display_check_in_photo',
            'worked_minutes',
            'overtime_minutes',
        )
        if obj.check_in and not obj.check_out:
            return (
                ('RINGKASAN CHECK-IN', {
                    'fields': summary_fields,
                }),
                ('CHECK-OUT HARI INI', {
                    'description': (
                        'Ambil foto check-out langsung dari kamera. Waktu '
                        'dan lokasi akan diisi otomatis.'
                    ),
                    'fields': (
                        'photo_check_out',
                        'check_out_location',
                        'check_out_gps_accuracy',
                    ),
                }),
            )
        return (
            ('RINGKASAN ABSENSI', {
                'fields': summary_fields + (
                    'check_out',
                    'check_out_location_label',
                    'check_out_accuracy_meters',
                    'check_out_distance_meters',
                    'display_check_out_photo',
                ),
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields
        if obj is None:
            return ()
        readonly = [
            'user',
            'date',
            'status',
            'work_policy',
            'work_mode',
            'check_in',
            'check_in_location_label',
            'check_in_accuracy_meters',
            'check_in_distance_meters',
            'display_check_in_photo',
            'worked_minutes',
            'overtime_minutes',
        ]
        if obj.check_out or not obj.check_in:
            readonly += [
                'check_out',
                'check_out_location_label',
                'check_out_accuracy_meters',
                'check_out_distance_meters',
                'display_check_out_photo',
            ]
        return readonly

    def get_form(self, request, obj=None, change=False, **kwargs):
        form_class = super().get_form(
            request,
            obj,
            change=change,
            **kwargs,
        )

        class RequestAwareAttendanceForm(form_class):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs['request'] = request
                super().__init__(*args, **inner_kwargs)

        return RequestAwareAttendanceForm

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            profile = request.user.profile
            policy = (
                form.cleaned_data.get('work_policy')
                or obj.work_policy
                or profile.work_policy
            )
            now = timezone.now()

            if not change:
                work_mode = (
                    form.cleaned_data.get('work_mode')
                    or AttendanceWorkMode.OFFICE
                )
                current_point = form.cleaned_data.get(
                    'check_in_location'
                )
            else:
                work_mode = (
                    obj.work_mode or AttendanceWorkMode.OFFICE
                )
                current_point = form.cleaned_data.get(
                    'check_out_location'
                )

            location_result = getattr(
                form,
                'attendance_location_validation',
                None,
            ) or validate_attendance_location(
                profile,
                policy,
                work_mode,
                current_point,
            )

            if not change:
                obj.user = profile
                obj.date = timezone.localdate()
                obj.work_policy = policy
                obj.work_mode = work_mode
                obj.check_in = now
                obj.check_in_location = location_result.current_point
                obj.check_in_location_label = location_result.label
                obj.check_in_accuracy_meters = form.cleaned_data.get(
                    'check_in_gps_accuracy'
                )
                obj.check_in_distance_meters = (
                    location_result.distance_meters
                )
                obj.status_override = None
                obj.status_override_reason = ''
            else:
                obj.check_out = now
                obj.check_out_location = location_result.current_point
                obj.check_out_location_label = location_result.label
                obj.check_out_accuracy_meters = form.cleaned_data.get(
                    'check_out_gps_accuracy'
                )
                obj.check_out_distance_meters = (
                    location_result.distance_meters
                )
        super().save_model(request, obj, form, change)

    formfield_overrides = {
        gis_models.PointField: {
            'widget': mapwidgets.GoogleMapPointFieldWidget
        }
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'work_policy':
            kwargs['queryset'] = WorkPolicy.objects.filter(
                is_active=True
            ).order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        if not request.user.is_superuser:
            try:
                if request.user.profile.work_policy_id:
                    initial['work_policy'] = (
                        request.user.profile.work_policy_id
                    )
            except Profile.DoesNotExist:
                pass
        return initial

    def has_add_permission(self, request):
        allowed = super().has_add_permission(request)
        if request.user.is_superuser or not allowed:
            return allowed
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return False
        return not Attendance.objects.filter(
            user=profile,
            date=timezone.localdate(),
        ).exists()

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj)
        if request.user.is_superuser or obj is None or not allowed:
            return allowed
        return (
            obj.user.user_id == request.user.id
            and obj.date == timezone.localdate()
            and bool(obj.check_in)
            and not obj.check_out
        )

    def has_delete_permission(self, request, obj=None):
        return (
            request.user.is_superuser
            and super().has_delete_permission(request, obj)
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop('restore_selected', None)
        return actions
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if 'is_deleted__exact' not in request.GET:
            qs = qs.filter(is_deleted=False)
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
class AttendanceInline(TabularInline):
    tab = True
    model           = Attendance
    extra           = 1
    classes         = ['collapse',]
    fields          = ('date', 'check_in_location_label', 'check_out_location_label', 'check_in', 'check_out', 'check_in_location', 'check_out_location', 'status', 'photo_check_in', 'photo_check_out')
    readonly_fields = ('date', 'check_in', 'check_out', 'status')

    formfield_overrides = {
        gis_models.PointField: {'widget': mapwidgets.GoogleMapPointFieldWidget}
    }
    
class LeaveRequestInline(TabularInline):
    tab = True
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
class ProfileAdmin(SoftDeleteAdminMixin, ModelAdmin):
    personal_fields = (
        'profile_picture',
        'full_name',
        'gender',
        'birthday',
        'phone_number',
    )
    organization_fields = (
        'user',
        'location',
        'role',
        'status',
        'join_date',
        'work_policy',
        'is_active',
    )
    directory_fields = (
        'profile_picture',
        'display_photo',
        'full_name',
        'role',
        'gender',
        'status',
        'phone_number',
        'work_policy',
        'is_active',
    )
    admin_select_related = ('user', 'location', 'work_policy')
    autocomplete_fields = ('user', 'location', 'work_policy')
    list_display    = ('full_name', 'display_photo_view', 'user', 'role', 'gender', 'status', 'phone_number', 'is_active')
    inlines = [TeamMemberInline, SignatureInline, InitialInline]
    fieldsets = (
        (None, {
            "fields": (
                ('profile_picture', 'display_photo'),
                'user', 'location', 'full_name', 'role',
                'gender', 'status', 'birthday',
                'join_date', 'phone_number', 'work_policy',
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
    list_filter     = ('role', 'gender', 'status', 'is_active', ('birthday', RangeDateFilter), ('join_date', RangeDateFilter), 'is_deleted')
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
        if not request.user.is_superuser:
            qs = qs.filter(is_active=True)
        return qs

    def has_view_permission(self, request, obj=None):
        return bool(
            request.user.is_active
            and request.user.is_staff
        )

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not request.user.is_active or not request.user.is_staff:
            return False
        if obj is None:
            return hasattr(request.user, 'profile')
        return obj.user_id == request.user.pk

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        if not request.user.is_superuser:
            return {}
        return super().get_actions(request)

    def get_inlines(self, request, obj):
        if request.user.is_superuser:
            return self.inlines
        if obj is not None and obj.user_id == request.user.pk:
            return (SignatureInline, InitialInline)
        return ()

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return self.fieldsets
        if obj.user_id != request.user.pk:
            return (
                ('PROFIL STAFF', {
                    'description': (
                        'Profil ini hanya dapat dilihat. Data pribadi dan '
                        'riwayat staff tidak ditampilkan.'
                    ),
                    'fields': self.directory_fields,
                }),
            )
        return (
            ('DATA PRIBADI', {
                'description': (
                    'Anda dapat memperbarui data pribadi sendiri. Data '
                    'organisasi hanya dapat diubah oleh superuser.'
                ),
                'fields': (
                    ('profile_picture', 'display_photo'),
                    'full_name',
                    'gender',
                    'birthday',
                    'phone_number',
                ),
            }),
            ('DATA ORGANISASI', {
                'fields': self.organization_fields,
            }),
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            if obj is not None and obj.user_id != request.user.pk:
                readonly_fields.extend(self.directory_fields)
            else:
                readonly_fields.extend(self.organization_fields)
        return tuple(dict.fromkeys(readonly_fields))
    
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
# class SignatureAdmin(ModelAdmin):
#     list_display   = ('user', 'expire_at', 'created_at')
#     list_filter    = ('expire_at',)
#     search_fields  = ('user__full_name',)
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# @admin.register(Initial)
# class InitialAdmin(ModelAdmin):
#     list_display   = ('user', 'expire_at', 'created_at')
#     list_filter    = ('expire_at',)
#     search_fields  = ('user__full_name',)
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# ──────────────── LeaveRequests ────────────────

class SignatureOnLeaveRequestInline(TabularInline):
    tab = True
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
class LeaveRequestAdmin(
    ApprovalWorkflowAdminMixin, SoftDeleteAdminMixin, ModelAdmin
):
    approval_workflow_type = 'leave_request'
    approval_required_role = 'project_admin,admin'
    autocomplete_fields = ('user',)
    admin_select_related = ('user', 'approved_by')
    list_display    = ('user' ,'status', 'display_photo_view', 'start_date', 'end_date', 'reason', 'approved_by', 'approved_date')
    list_filter     = ('user' ,'status', ('start_date', RangeDateFilter), ('end_date', RangeDateFilter), ('approved_date', RangeDateFilter), 'approved_by', 'is_deleted')
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
                obj.approved_by = getattr(request.user, 'profile', None)
                obj.approved_date = timezone.now()
            elif previous.status != obj.status:
                obj.approved_by = None
                obj.approved_date = None
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
class NotificationsAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('user',)
    autocomplete_fields = ('user',)
    list_display = ('title', 'user', 'category', 'is_read', 'sent_at')
    list_filter = (
        'category', 'is_read', ('sent_at', RangeDateFilter), 'is_deleted',
    )
    search_fields   = ('title', 'user__full_name', 'message')
    readonly_fields = (
        'id', 'sent_at', 'created_at', 'created_by',
        'updated_at', 'updated_by', 'is_deleted',
        'deleted_at', 'deleted_by',
    )
    actions = ['restore_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Superuser boleh lihat semua
        if request.user.is_superuser:
            return qs
        # Non-superuser: hanya lihat record miliknya
        return qs.filter(user__user=request.user)


@admin.register(WorkPolicy)
class WorkPolicyAdmin(SoftDeleteAdminMixin, ModelAdmin):
    list_display = (
        'name', 'office_location', 'work_start', 'work_end', 'late_grace_minutes',
        'overtime_after_minutes', 'geofence_radius_meters', 'allow_wfh',
        'wfh_geofence_radius_meters', 'is_active',
    )
    list_filter = ('allow_wfh', 'is_active', 'is_deleted')
    search_fields = ('name',)
    admin_select_related = ('office_location',)
    autocomplete_fields = ('office_location',)
    readonly_fields = (
        'created_at', 'created_by', 'updated_at', 'updated_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )


@admin.register(Holiday)
class HolidayAdmin(SoftDeleteAdminMixin, ModelAdmin):
    list_display = ('date', 'name', 'weekday_label', 'source')
    list_filter = ('source', ('date', RangeDateFilter), 'is_deleted')
    search_fields = ('name',)
    date_hierarchy = 'date'
    list_before_template = 'admin/team/holiday/calendar.html'
    readonly_fields = (
        'created_at', 'created_by', 'updated_at', 'updated_by',
        'is_deleted', 'deleted_at', 'deleted_by',
    )

    class Media:
        css = {
            'all': ('admin/css/holiday_calendar.css',),
        }

    @admin.display(description='Hari', ordering='date')
    def weekday_label(self, obj):
        return WEEKDAY_NAMES[obj.date.weekday()]

    def get_urls(self):
        custom_urls = [
            path(
                'sync/',
                self.admin_site.admin_view(self.sync_view),
                name='team_holiday_sync',
            ),
        ]
        return custom_urls + super().get_urls()

    def _calendar_anchor(self, request):
        """Bulan yang sedang ditampilkan pada kalender."""
        today = timezone.localdate()
        try:
            year = int(request.GET.get('cal_year') or today.year)
            month = int(request.GET.get('cal_month') or today.month)
            return date(year, month, 1)
        except (TypeError, ValueError):
            return today.replace(day=1)

    def _month_url(self, anchor):
        return (
            f"{reverse('admin:team_holiday_changelist')}"
            f'?cal_year={anchor.year}&cal_month={anchor.month}'
        )

    def sync_view(self, request):
        """Tarik kalender libur nasional untuk bulan yang sedang dibuka."""
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method != 'POST':
            return HttpResponseRedirect(
                reverse('admin:team_holiday_changelist')
            )

        from team.holidays import (
            sync_indonesian_holidays,
            sync_summary_line,
        )

        today = timezone.localdate()
        try:
            year = int(request.POST.get('year') or today.year)
        except (TypeError, ValueError):
            year = today.year

        scope = request.POST.get('scope') or 'month'
        if scope == 'year':
            month = None
        else:
            try:
                month = int(request.POST.get('month') or today.month)
            except (TypeError, ValueError):
                month = today.month
            if not 1 <= month <= 12:
                month = today.month

        summary = sync_indonesian_holidays(year, month)
        self.message_user(
            request,
            sync_summary_line(summary),
            level=(
                messages.SUCCESS
                if summary['created'] or summary['updated']
                else messages.INFO
            ),
        )
        return HttpResponseRedirect(
            self._month_url(date(year, month or today.month, 1))
        )

    def _holiday_calendar(self, request, anchor):
        today = timezone.localdate()
        last_day = calendar.monthrange(anchor.year, anchor.month)[1]
        month_end = anchor.replace(day=last_day)

        holidays = {
            holiday.date: holiday
            for holiday in Holiday.objects.filter(
                date__range=(anchor, month_end),
            )
        }

        weeks = []
        for week in calendar.Calendar(firstweekday=0).monthdatescalendar(
            anchor.year, anchor.month
        ):
            cells = []
            for day in week:
                holiday = holidays.get(day)
                cells.append({
                    'date': day,
                    'day': day.day,
                    'in_month': day.month == anchor.month,
                    'is_weekend': day.weekday() >= 5,
                    'is_today': day == today,
                    'holiday': holiday,
                    'change_url': (
                        reverse(
                            'admin:team_holiday_change',
                            args=(holiday.pk,),
                        )
                        if holiday
                        else None
                    ),
                })
            weeks.append(cells)

        previous_anchor = (anchor - timedelta(days=1)).replace(day=1)
        next_anchor = (month_end + timedelta(days=1)).replace(day=1)
        agenda = [holidays[key] for key in sorted(holidays)]

        return {
            'anchor': anchor,
            'label': f'{MONTH_NAMES[anchor.month]} {anchor.year}',
            'weekday_names': WEEKDAY_SHORT,
            'weeks': weeks,
            'agenda': agenda,
            'total': len(agenda),
            'national_total': sum(
                1
                for holiday in agenda
                if holiday.source == HolidaySource.NATIONAL
            ),
            'manual_total': sum(
                1
                for holiday in agenda
                if holiday.source == HolidaySource.MANUAL
            ),
            'previous_url': self._month_url(previous_anchor),
            'next_url': self._month_url(next_anchor),
            'today_url': self._month_url(today.replace(day=1)),
            'sync_url': reverse('admin:team_holiday_sync'),
            'can_sync': self.has_add_permission(request),
        }

    def changelist_view(self, request, extra_context=None):
        # cal_year/cal_month hanya menggerakkan kalender dan bukan filter
        # changelist. Django menolak querystring yang tidak dikenalnya, jadi
        # parameter ini dibaca lebih dulu lalu dikeluarkan dari request.
        anchor = self._calendar_anchor(request)
        if 'cal_year' in request.GET or 'cal_month' in request.GET:
            params = request.GET.copy()
            params.pop('cal_year', None)
            params.pop('cal_month', None)
            request.GET = params
            request.META['QUERY_STRING'] = params.urlencode()

        response = super().changelist_view(request, extra_context)
        if hasattr(response, 'context_data'):
            response.context_data['holiday_calendar'] = (
                self._holiday_calendar(request, anchor)
            )
        return response

# ──────────────── SubContractor & Workers ────────────────

class SubContractorWorkerInline(TabularInline):
    tab = True
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

class SubContractorOnProjectInline(TabularInline):
    tab = True
    model  = SubContractorOnProject
    extra  = 0
    classes = ['collapse',]
    fields = ('project', 'is_active', 'descriptions')

@admin.register(SubContractor)
class SubContractorAdmin(SoftDeleteAdminMixin, ModelAdmin):
    admin_select_related = ('locations',)
    autocomplete_fields = ('locations',)
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
# class SubContractorWorkerAdmin(ModelAdmin):
#     list_display   = ('worker_name', 'subcon', 'contact_number')
#     list_filter    = ('subcon',)
#     search_fields  = ('worker_name', 'subcon__name')
#     readonly_fields = ('id', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

# ──────────────── SubContractorOnProject ────────────────

# @admin.register(SubContractorOnProject)
# class SubContractorOnProjectAdmin(ModelAdmin):
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
