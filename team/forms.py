# app_name/forms.py

from django import forms
from django.forms import FileInput
from django.contrib.gis.db import models as gis_models
from.models import Attendance

class CameraInputWidget(FileInput):
    """
    Widget kustom yang menambahkan atribut 'capture="user"' untuk memaksa kamera depan.
    """
    def __init__(self, attrs=None):
        default_attrs = {'accept': 'image/*', 'capture': 'user'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class AttendanceAdminForm(forms.ModelForm):
    
    # Hidden field untuk membawa status superuser ke JS
    request_user_is_superuser = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)
    
    class Meta:
        model = Attendance
        fields = '__all__'
        widgets = {
            'photo_check_in': CameraInputWidget,
            'photo_check_out': CameraInputWidget,
        }
    
    # Harus di-override agar bisa menerima 'request' dari ModelAdmin
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None) # Menerima request dari ModelAdmin.get_form
        super().__init__(*args, **kwargs)
        
        is_superuser = request and request.user.is_superuser
        self.initial['request_user_is_superuser'] = is_superuser
        
        if not is_superuser:
            instance = self.instance
            
            # Non-superuser Logic:
            # Poin 3 & 4: Nonaktifkan Check-out dan Lokasi Check-out
            has_checked_in = instance and bool(instance.photo_check_in)
            
            # Jika instance sudah ada tetapi belum check-in, atau ini entri baru
            if not has_checked_in:
                # Disabled di Python memastikan field tidak dapat diisi saat dimuat
                self.fields['photo_check_out'].disabled = True
                self.fields['check_out_location'].disabled = True 

    def clean(self):
        cleaned_data = super().clean()
        is_superuser = self.initial.get('request_user_is_superuser', False)

        if not is_superuser:
            # Dapatkan nilai photo_in (baik dari instance lama atau upload baru)
            photo_in = self.instance.photo_check_in or cleaned_data.get('photo_check_in')
            photo_out = cleaned_data.get('photo_check_out')

            # Poin 3: Validasi Server-side
            if photo_out and not photo_in:
                raise forms.ValidationError(
                    "Check-out photo cannot be uploaded before Check-in photo has been recorded."
                )

        return cleaned_data