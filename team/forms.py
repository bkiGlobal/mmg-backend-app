from django import forms
from django.utils import timezone
from .models import Attendance
from django.contrib.gis.geos import Point

class AttendanceAdminForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Jika check_out belum diisi, sembunyikan photo_check_out
        if not self.instance or not self.instance.check_in:
            self.fields['photo_check_out'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        date = cleaned_data.get('date') or timezone.now().date()

        if not self.instance.pk:
            if Attendance.objects.filter(user=user, date=date).exists():
                raise forms.ValidationError("Anda sudah melakukan absensi hari ini.")

        # Jika check_in belum ada → artinya ini adalah proses check in
        if not self.instance.check_in and cleaned_data.get("photo_check_in"):
            cleaned_data["check_in"] = timezone.now()

            # Ambil lat/lng dari form hidden (pakai JS untuk isi)
            lat = float(self.data.get('check_in_lat', 0))
            lng = float(self.data.get('check_in_lng', 0))
            cleaned_data["check_in_location"] = Point(lng, lat)

        # Jika sudah ada check_in → proses check out
        elif self.instance.check_in and cleaned_data.get("photo_check_out") and not self.instance.check_out:
            cleaned_data["check_out"] = timezone.now()

            lat = float(self.data.get('check_out_lat', 0))
            lng = float(self.data.get('check_out_lng', 0))
            cleaned_data["check_out_location"] = Point(lng, lat)

        return cleaned_data
