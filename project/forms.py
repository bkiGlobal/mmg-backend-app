from django import forms
from django.apps import apps

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = apps.get_model('project', 'Schedule')
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BoqModel = apps.get_model('finance', 'BillOfQuantityItemDetail')
        self.fields['boq_item'] = forms.ModelChoiceField(queryset=BoqModel.objects.all())
