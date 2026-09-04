from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet
from django.utils import timezone
from unfold.widgets import (
    UnfoldAdminFileFieldWidget,
    UnfoldBooleanSwitchWidget,
)

from core.models import FinanceType, PaymentVia
from project.models import Project


SHEET_INPUT_CLASS = 'mmg-sheet-input'


class BaseLedgerSpreadsheetRowForm(forms.Form):
    project = forms.ModelChoiceField(
        label='Project',
        queryset=Project.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': SHEET_INPUT_CLASS}),
    )
    other = forms.CharField(
        label='Ledger lain',
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'placeholder': 'Isi jika bukan project',
            }
        ),
    )
    date = forms.DateField(
        label='Tanggal',
        initial=timezone.localdate,
        widget=forms.DateInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'type': 'date',
            }
        ),
    )
    description = forms.CharField(
        label='Keterangan',
        widget=forms.TextInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'placeholder': 'Uraian transaksi',
            }
        ),
    )
    debet = forms.DecimalField(
        label='Debet',
        required=False,
        min_value=0,
        max_digits=16,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'min': '0',
                'step': '0.01',
                'inputmode': 'decimal',
                'placeholder': '0',
            }
        ),
    )
    credit = forms.DecimalField(
        label='Credit',
        required=False,
        min_value=0,
        max_digits=16,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'min': '0',
                'step': '0.01',
                'inputmode': 'decimal',
                'placeholder': '0',
            }
        ),
    )
    photo_proof = forms.ImageField(
        label='Bukti',
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'accept': 'image/*',
            }
        ),
    )

    field_order = (
        'project',
        'other',
        'date',
        'description',
        'debet',
        'credit',
        'photo_proof',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.order_by(
            'project_code',
            'project_name',
        )
        self.order_fields(self.field_order)

    def clean(self):
        cleaned_data = super().clean()
        if self._errors:
            return cleaned_data

        project = cleaned_data.get('project')
        other = (cleaned_data.get('other') or '').strip()
        debet = cleaned_data.get('debet') or 0
        credit = cleaned_data.get('credit') or 0
        cleaned_data['other'] = other
        cleaned_data['debet'] = debet
        cleaned_data['credit'] = credit

        if bool(project) == bool(other):
            raise ValidationError(
                'Pilih tepat satu ledger: project atau ledger lain.'
            )
        if debet > 0 and credit > 0:
            raise ValidationError(
                'Satu baris tidak boleh memiliki debet dan credit sekaligus.'
            )
        if debet == 0 and credit == 0:
            raise ValidationError(
                'Isi salah satu nilai debet atau credit.'
            )
        return cleaned_data


class FinanceDataSpreadsheetRowForm(BaseLedgerSpreadsheetRowForm):
    pass


class PettyCashSpreadsheetRowForm(BaseLedgerSpreadsheetRowForm):
    type = forms.ModelChoiceField(
        label='Tipe',
        queryset=FinanceType.objects.none(),
        widget=forms.Select(attrs={'class': SHEET_INPUT_CLASS}),
    )
    payment_via = forms.ModelChoiceField(
        label='Pembayaran',
        queryset=PaymentVia.objects.none(),
        widget=forms.Select(attrs={'class': SHEET_INPUT_CLASS}),
    )
    photo_proof = forms.ImageField(
        label='Bukti',
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                'class': SHEET_INPUT_CLASS,
                'accept': 'image/*',
            }
        ),
    )
    field_order = (
        'project',
        'other',
        'date',
        'type',
        'payment_via',
        'description',
        'debet',
        'credit',
        'photo_proof',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].queryset = FinanceType.objects.order_by('name')
        self.fields['payment_via'].queryset = PaymentVia.objects.order_by(
            'name'
        )
        self.order_fields(self.field_order)


class LedgerSpreadsheetFormSet(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active_forms = [
            form
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get('DELETE')
            and form.has_changed()
        ]
        if not active_forms:
            raise ValidationError('Isi minimal satu baris transaksi.')


class MultiSheetImportForm(forms.Form):
    file = forms.FileField(
        label="Pilih file Excel (.xlsx)",
        help_text=(
            "File harus memiliki sheet Expense, ExpenseDetail, "
            "dan ExpenseForMaterial."
        ),
        widget=UnfoldAdminFileFieldWidget(
            attrs={'accept': '.xlsx'},
        ),
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label='Validasi saja (tidak menyimpan)',
        help_text='Matikan opsi ini setelah hasil validasi dinyatakan aman.',
        widget=UnfoldBooleanSwitchWidget(),
    )
