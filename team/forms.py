# app_name/forms.py

from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Attendance,
    AttendanceWorkMode,
    Profile,
    WorkPolicy,
)
from .services import validate_attendance_location


REPORT_INPUT_CLASSES = (
    'border border-base-200 bg-white font-medium px-3 py-2 '
    'rounded-default shadow-xs text-font-default-light text-sm w-full '
    'focus:outline-2 focus:-outline-offset-2 focus:outline-primary-600 '
    'dark:bg-base-900 dark:border-base-700 dark:text-font-default-dark '
    'dark:scheme-dark'
)


class AttendanceReportForm(forms.Form):
    """Parameter laporan attendance yang berlaku untuk Excel dan PDF."""

    MAX_REPORT_DAYS = 366
    OUTPUT_FORMATS = (
        ('xlsx', 'Excel (.xlsx)'),
        ('pdf', 'PDF (.pdf)'),
    )

    date_from = forms.DateField(
        label='Tanggal mulai',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': REPORT_INPUT_CLASSES,
            },
        ),
    )
    date_to = forms.DateField(
        label='Tanggal akhir',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': REPORT_INPUT_CLASSES,
            },
        ),
    )
    output_format = forms.ChoiceField(
        label='Format laporan',
        choices=OUTPUT_FORMATS,
        widget=forms.Select(
            attrs={'class': REPORT_INPUT_CLASSES},
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        if not date_from or not date_to:
            return cleaned_data
        if date_to < date_from:
            raise forms.ValidationError(
                'Tanggal akhir tidak boleh sebelum tanggal mulai.'
            )
        if date_to - date_from > timedelta(
            days=self.MAX_REPORT_DAYS - 1
        ):
            raise forms.ValidationError(
                f'Rentang laporan maksimal {self.MAX_REPORT_DAYS} hari.'
            )
        return cleaned_data


class CameraInputWidget(forms.FileInput):
    """Input tersembunyi yang hanya diisi oleh hasil kamera browser."""

    def __init__(self, attrs=None):
        default_attrs = {
            'accept': 'image/*',
            'capture': 'user',
            'class': 'mmg-camera-source-input',
            'data-mmg-camera-required': 'true',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class StyledImageInput(forms.ClearableFileInput):
    """Pemilih file yang tetap tersedia untuk koreksi oleh superuser."""

    def __init__(self, attrs=None):
        default_attrs = {
            'accept': 'image/*',
            'class': 'mmg-styled-file-input',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class AttendanceAdminForm(forms.ModelForm):
    check_in_gps_accuracy = forms.FloatField(
        required=False,
        min_value=0,
        widget=forms.HiddenInput(),
    )
    check_out_gps_accuracy = forms.FloatField(
        required=False,
        min_value=0,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Attendance
        fields = '__all__'

    class Media:
        css = {
            'all': ('admin/css/attendance_camera.css',),
        }
        js = (
            'admin/js/attendance_geolocation.js',
            'admin/js/attendance_camera.js',
        )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.request = request

        is_superuser = bool(request and request.user.is_superuser)
        photo_configuration = {
            'photo_check_in': (
                'Foto check-in',
                'check_in_location',
                'check_in_gps_accuracy',
            ),
            'photo_check_out': (
                'Foto check-out',
                'check_out_location',
                'check_out_gps_accuracy',
            ),
        }
        for field_name, configuration in photo_configuration.items():
            if field_name not in self.fields:
                continue
            label, location_field, accuracy_field = configuration
            if is_superuser:
                self.fields[field_name].widget = StyledImageInput()
            else:
                self.fields[field_name].widget = CameraInputWidget(
                    attrs={
                        'data-mmg-camera-label': label,
                        'data-mmg-camera-facing-mode': 'user',
                        'data-mmg-location-input': (
                            f'id_{location_field}'
                        ),
                        'data-mmg-accuracy-input': (
                            f'id_{accuracy_field}'
                        ),
                    }
                )

        if not is_superuser:
            for field_name in (
                'check_in_location',
                'check_out_location',
                'check_in_gps_accuracy',
                'check_out_gps_accuracy',
            ):
                if field_name in self.fields:
                    self.fields[field_name].widget = forms.HiddenInput()

            if 'work_policy' in self.fields:
                self.fields['work_policy'].queryset = (
                    WorkPolicy.objects.filter(is_active=True)
                    .order_by('name')
                )
                self.fields['work_policy'].required = True
                self.fields['work_policy'].help_text = (
                    'Pilih lokasi kerja Anda saat ini, misalnya kantor, '
                    'dinas, atau lokasi proyek. Hanya policy aktif yang '
                    'ditampilkan.'
                )
                if (
                    request
                    and hasattr(request.user, 'profile')
                    and request.user.profile.work_policy_id
                ):
                    self.initial.setdefault(
                        'work_policy',
                        request.user.profile.work_policy_id,
                    )
            if (
                self.instance._state.adding
                and 'photo_check_in' in self.fields
            ):
                self.fields['photo_check_in'].required = True
            if (
                not self.instance._state.adding
                and not self.instance.check_out
                and 'photo_check_out' in self.fields
            ):
                self.fields['photo_check_out'].required = True

    def clean(self):
        cleaned_data = super().clean()
        is_superuser = bool(
            self.request and self.request.user.is_superuser
        )

        if is_superuser:
            has_check_in = bool(
                cleaned_data.get('check_in')
                or cleaned_data.get('photo_check_in')
                or self.instance.check_in
                or self.instance.photo_check_in
            )
            has_manual_status = bool(
                cleaned_data.get('status_override')
                or self.instance.status
            )
            if not has_check_in and not has_manual_status:
                raise forms.ValidationError(
                    'Isi data check-in atau gunakan override status.'
                )
        else:
            try:
                profile = self.request.user.profile
            except (AttributeError, Profile.DoesNotExist):
                raise forms.ValidationError(
                    'Profile pengguna belum tersedia.'
                )

            if self.instance._state.adding:
                policy = cleaned_data.get('work_policy')
                if policy is None:
                    raise forms.ValidationError(
                        'Work policy wajib dipilih.'
                    )
                if Attendance.objects.filter(
                    user=profile,
                    date=timezone.localdate(),
                ).exists():
                    raise forms.ValidationError(
                        'Anda sudah memiliki data absensi hari ini.'
                    )
            else:
                policy = (
                    self.instance.work_policy
                    or profile.work_policy
                )
                if self.instance.date != timezone.localdate():
                    raise forms.ValidationError(
                        'User hanya dapat check-out pada absensi hari ini.'
                    )
                if self.instance.check_out:
                    raise forms.ValidationError(
                        'Anda sudah check-out hari ini.'
                    )

            try:
                if not self.instance._state.adding:
                    work_mode = (
                        self.instance.work_mode
                        or AttendanceWorkMode.OFFICE
                    )
                    current_point = cleaned_data.get(
                        'check_out_location'
                    )
                else:
                    work_mode = (
                        cleaned_data.get('work_mode')
                        or AttendanceWorkMode.OFFICE
                    )
                    current_point = cleaned_data.get(
                        'check_in_location'
                    )
                self.attendance_location_validation = (
                    validate_attendance_location(
                        profile,
                        policy,
                        work_mode,
                        current_point,
                    )
                )
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)

        return cleaned_data
