from django import forms

class MultiSheetImportForm(forms.Form):
    file = forms.FileField(
        label="Pilih file Excel (.xlsx)",
        help_text="File harus memiliki sheet 'Income' dan 'IncomeDetail'"
    )