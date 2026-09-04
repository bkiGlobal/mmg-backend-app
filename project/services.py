from django.db import transaction

from core.models import DocumentType


def _source_configuration(source):
    if source._meta.label_lower == 'project.drawing':
        return {
            'document_type': source.drawing_type,
            'versions': source.drawing_versions,
            'file_field': 'drawing_file',
            'number_field': 'document_number',
        }
    if source._meta.label_lower == 'finance.billofquantity':
        document_type, _ = DocumentType.objects.get_or_create(
            name='Bill of Quantity'
        )
        return {
            'document_type': document_type,
            'versions': source.boq_versions,
            'file_field': 'boq_file',
            'number_field': 'document_number',
        }
    if source._meta.label_lower == 'finance.paymentrequest':
        document_type, _ = DocumentType.objects.get_or_create(
            name='Payment Request'
        )
        return {
            'document_type': document_type,
            'versions': source.payment_versions,
            'file_field': 'payment_file',
            'number_field': 'payment_number',
        }
    return None


@transaction.atomic
def sync_approved_document(source):
    """Sinkronkan sumber approved tanpa menghapus riwayat versi dokumen."""
    from project.models import (
        ApprovalLevel,
        Document,
        DocumentStatus,
        DocumentVersion,
    )

    configuration = _source_configuration(source)
    if configuration is None or source.status != DocumentStatus.APPROVED:
        return None

    document_name = getattr(
        source, 'document_name', getattr(source, 'payment_name', '')
    )
    document, _ = Document.all_objects.update_or_create(
        project=source.project,
        document_type=configuration['document_type'],
        document_name=document_name,
        defaults={
            'status': DocumentStatus.APPROVED,
            'approval_required': getattr(source, 'approval_required', True),
            'approval_level': getattr(
                source, 'approval_level', ApprovalLevel.LEVEL_1
            ),
            'issue_date': source.issue_date,
            # Document.due_date wajib terisi, sedangkan sebagian data sumber
            # lama masih mengizinkan due_date kosong.
            'due_date': source.due_date or source.issue_date,
            'is_deleted': False,
            'deleted_at': None,
            'deleted_by': None,
        },
    )

    version = (
        configuration['versions']
        .filter(status=DocumentStatus.APPROVED)
        .order_by('-created_at')
        .first()
    )
    if version is None:
        return document

    number = getattr(version, configuration['number_field'])
    DocumentVersion.all_objects.update_or_create(
        document=document,
        document_number=number,
        defaults={
            'document_file': getattr(version, configuration['file_field']),
            'title': version.title,
            'status': DocumentStatus.APPROVED,
            'notes': version.notes,
            'is_deleted': False,
            'deleted_at': None,
            'deleted_by': None,
        },
    )
    return document
