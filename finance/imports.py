import uuid

import pandas as pd
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import ExpenseDetail, ExpenseForMaterial, ExpenseOnProject


def _value(row, *names, default=None):
    for name in names:
        if name not in row:
            continue
        value = row[name]
        if pd.isna(value):
            continue
        return value
    return default


def _pk(row):
    value = _value(row, 'id')
    return value or uuid.uuid4()


def _date(value):
    if hasattr(value, 'date'):
        return value.date()
    return value


def _restore_imported_object(obj):
    obj.is_deleted = False
    obj.deleted_at = None
    obj.deleted_by = None


@transaction.atomic
def import_expense_workbook(df_expense, df_detail, df_material):
    """Import workbook secara atomik; calculated fields selalu dihitung ulang."""
    counts = {
        'expense_created': 0,
        'expense_updated': 0,
        'detail_created': 0,
        'detail_updated': 0,
        'material_created': 0,
        'material_updated': 0,
    }
    affected_expense_ids = set()

    for index, row in df_expense.iterrows():
        try:
            pk = _pk(row)
            expense = ExpenseOnProject.all_objects.filter(pk=pk).first()
            created = expense is None
            if created:
                expense = ExpenseOnProject(pk=pk)
            expense.project_id = _value(row, 'project', 'project_id')
            expense.date = _date(_value(row, 'date'))
            expense.notes = _value(row, 'notes', default='') or ''
            photo = _value(row, 'photo_proof')
            if photo:
                expense.photo_proof = photo
            _restore_imported_object(expense)
            expense.save()
            affected_expense_ids.add(expense.pk)
            key = 'expense_created' if created else 'expense_updated'
            counts[key] += 1
        except Exception as exc:
            raise ValidationError(
                f'Sheet Expense baris {index + 2}: {exc}'
            ) from exc

    for index, row in df_detail.iterrows():
        try:
            pk = _pk(row)
            detail = ExpenseDetail.all_objects.filter(pk=pk).first()
            created = detail is None
            if created:
                detail = ExpenseDetail(pk=pk)
            detail.expense_id = _value(
                row, 'expense', 'expense_id', 'expense_on_project'
            )
            detail.category_id = _value(row, 'category', 'category_id')
            detail.unit_id = _value(row, 'unit', 'unit_id')
            detail.name = _value(row, 'name', default='') or ''
            detail.quantity = _value(row, 'quantity', default=0)
            detail.unit_price = _value(row, 'unit_price', default=0)
            detail.discount = _value(row, 'discount', default=0)
            detail.discount_type = _value(row, 'discount_type')
            detail.notes = _value(row, 'notes', default='') or ''
            _restore_imported_object(detail)
            detail.save(recalculate=False)
            affected_expense_ids.add(detail.expense_id)
            key = 'detail_created' if created else 'detail_updated'
            counts[key] += 1
        except Exception as exc:
            raise ValidationError(
                f'Sheet ExpenseDetail baris {index + 2}: {exc}'
            ) from exc

    for index, row in df_material.iterrows():
        try:
            pk = _pk(row)
            line = ExpenseForMaterial.all_objects.filter(pk=pk).first()
            created = line is None
            if created:
                line = ExpenseForMaterial(pk=pk)
            line.expense_id = _value(
                row, 'expense', 'expense_id', 'expense_on_project'
            )
            line.material_id = _value(row, 'material', 'material_id')
            line.category_id = _value(row, 'category', 'category_id')
            line.unit_id = _value(row, 'unit', 'unit_id')
            line.quantity = _value(row, 'quantity', default=0)
            line.unit_price = _value(row, 'unit_price', default=0)
            line.discount = _value(row, 'discount', default=0)
            line.discount_type = _value(row, 'discount_type')
            _restore_imported_object(line)
            line.save(recalculate=False)
            affected_expense_ids.add(line.expense_id)
            key = 'material_created' if created else 'material_updated'
            counts[key] += 1
        except Exception as exc:
            raise ValidationError(
                f'Sheet ExpenseForMaterial baris {index + 2}: {exc}'
            ) from exc

    for expense in ExpenseOnProject.all_objects.filter(
        pk__in=affected_expense_ids
    ):
        expense.recalculate_total()

    return counts
