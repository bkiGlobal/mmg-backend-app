from django import forms
from .models import Schedule, BillOfQuantityItemDetail

class ScheduleAdminForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields['boq_item'].queryset = BillOfQuantityItemDetail.objects.all()
        except Exception as e:
            import logging
            logging.error(f"Error loading boq_item queryset: {e}")
            self.fields['boq_item'].queryset = BillOfQuantityItemDetail.objects.none()
