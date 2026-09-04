"""Batch entry service for spreadsheet-style finance admin forms."""

from decimal import Decimal

from django.db import router, transaction
from djmoney.money import Money


def save_ledger_spreadsheet(model, formset, actor):
    """Validate every row, save atomically, then recalculate each ledger once."""
    objects = []
    model_field_names = {
        field.name
        for field in model._meta.concrete_fields
    }

    for form in formset.forms:
        data = getattr(form, 'cleaned_data', {})
        if (
            not data
            or data.get('DELETE')
            or not form.has_changed()
        ):
            continue

        values = {
            'project': data.get('project'),
            'other': data.get('other') or None,
            'date': data['date'],
            'description': data['description'],
            'debet': Money(data.get('debet') or Decimal('0'), 'IDR'),
            'credit': Money(data.get('credit') or Decimal('0'), 'IDR'),
            'photo_proof': data.get('photo_proof'),
            'created_by': actor,
        }
        if 'type' in model_field_names:
            values['type'] = data['type']
        if 'payment_via' in model_field_names:
            values['payment_via'] = data['payment_via']

        instance = model(**values)
        instance.full_clean()
        objects.append(instance)

    database = router.db_for_write(model)
    ledger_keys = set()
    with transaction.atomic(using=database):
        for instance in objects:
            instance.save(
                using=database,
                recalculate_balance=False,
            )
            ledger_keys.add(instance.ledger_key)

        for project_id, other in ledger_keys:
            model.recalculate_ledger(
                project_id=project_id,
                other=other,
                using=database,
            )

    return objects
