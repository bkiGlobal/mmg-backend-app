import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import models, router, transaction
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django_currentuser.middleware import get_current_authenticated_user


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet yang mempertahankan row dan menjalankan cascade soft-delete."""

    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def _base_rows_for_update(self):
        """
        Kunci hanya row dari tabel model utama.

        Queryset admin dapat membawa ``select_related()`` dengan LEFT OUTER
        JOIN. PostgreSQL tidak mengizinkan ``FOR UPDATE`` diterapkan ke sisi
        nullable join tersebut. Subquery tetap mempertahankan seluruh filter
        queryset asal, sedangkan query terluar hanya membaca dan mengunci
        tabel utama.
        """
        target_pks = self.values('pk')
        base_manager = getattr(
            self.model,
            'all_objects',
            self.model._base_manager,
        )
        return (
            base_manager.using(self.db)
            .filter(pk__in=target_pks)
            .order_by('pk')
            .select_for_update()
        )

    def delete(self, user=None, cascade_at=None):
        deleted_count = 0
        deleted_per_model = {}
        database = self.db

        with transaction.atomic(using=database):
            for obj in self._base_rows_for_update().iterator():
                count, per_model = obj.delete(
                    using=database,
                    user=user,
                    cascade_at=cascade_at,
                )
                model_label = obj._meta.label
                if not per_model:
                    per_model = {model_label: count}
                for label, model_count in per_model.items():
                    deleted_per_model[label] = (
                        deleted_per_model.get(label, 0) + model_count
                    )
                deleted_count += count

        return deleted_count, deleted_per_model

    def restore(self, user=None, cascade_at=None):
        restored_count = 0
        database = self.db

        with transaction.atomic(using=database):
            for obj in self._base_rows_for_update().iterator():
                obj.restore(
                    using=database,
                    user=user,
                    cascade_at=cascade_at,
                )
                restored_count += 1

        return restored_count

    def hard_delete(self):
        """Escape hatch eksplisit untuk maintenance yang benar-benar permanen."""
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class AuditModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_created_by'
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_updated_by'
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_deleted_by'
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()
    soft_delete_related = ()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from .images import compress_instance_images

        user = get_current_authenticated_user()
        update_fields = kwargs.get('update_fields')
        compress_instance_images(self, update_fields=update_fields)

        if self._state.adding:
            if self.created_by_id is None and user:
                self.created_by = user
        elif user:
            self.updated_by = user

        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add('updated_at')
            if self._state.adding and self.created_by_id:
                update_fields.add('created_by')
            elif not self._state.adding and user:
                update_fields.add('updated_by')
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    def _cascade_queryset(self, relation, using):
        related_model = relation.related_model
        if not issubclass(related_model, AuditModel):
            return None

        return related_model.all_objects.using(using).filter(
            **{relation.field.name: self}
        )

    def _cascade_relations(self, operation, using, user, cascade_at):
        affected_count = 0
        affected_per_model = {}

        for relation in self._meta.related_objects:
            on_delete = getattr(relation.field.remote_field, 'on_delete', None)
            accessor_name = relation.get_accessor_name()
            explicitly_related = accessor_name in self.soft_delete_related
            if on_delete is not models.CASCADE and not explicitly_related:
                continue

            queryset = self._cascade_queryset(relation, using)
            if queryset is None:
                continue

            if operation == 'delete':
                count, per_model = queryset.filter(
                    is_deleted=False
                ).delete(
                    user=user,
                    cascade_at=cascade_at,
                )
            else:
                count = queryset.filter(
                    is_deleted=True,
                    deleted_at=cascade_at,
                ).restore(user=user, cascade_at=cascade_at)
                per_model = {relation.related_model._meta.label: count}

            affected_count += count
            for label, model_count in per_model.items():
                affected_per_model[label] = (
                    affected_per_model.get(label, 0) + model_count
                )

        return affected_count, affected_per_model

    def delete(
        self, using=None, keep_parents=False, user=None, cascade_at=None
    ):
        """Soft-delete atomik, termasuk child AuditModel dengan FK CASCADE."""
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        actor = user or get_current_authenticated_user()

        with transaction.atomic(using=database):
            current = type(self).all_objects.using(database).select_for_update().get(
                pk=self.pk
            )
            if current.is_deleted:
                self.is_deleted = True
                self.deleted_at = current.deleted_at
                self.deleted_by_id = current.deleted_by_id
                return 0, {}

            now = cascade_at or timezone.now()
            self.is_deleted = True
            self.deleted_at = now
            self.updated_at = now
            update_fields = [
                'is_deleted', 'deleted_at', 'deleted_by', 'updated_at',
            ]
            if actor:
                self.deleted_by = actor
                self.updated_by = actor
                update_fields.append('updated_by')
            super().save(
                using=database,
                update_fields=update_fields,
            )
            child_count, child_per_model = self._cascade_relations(
                'delete', database, actor, now
            )

        model_label = self._meta.label
        child_per_model[model_label] = child_per_model.get(model_label, 0) + 1
        return child_count + 1, child_per_model

    def restore(self, using=None, user=None, cascade_at=None):
        """Pulihkan object dan child yang ikut berada pada tree CASCADE."""
        database = using or self._state.db or router.db_for_write(
            type(self), instance=self
        )
        actor = user or get_current_authenticated_user()

        with transaction.atomic(using=database):
            current = type(self).all_objects.using(database).select_for_update().get(
                pk=self.pk
            )
            if not current.is_deleted:
                self.is_deleted = False
                self.deleted_at = None
                self.deleted_by = None
                return self

            cascade_at = current.deleted_at
            now = timezone.now()
            self.is_deleted = False
            self.deleted_at = None
            self.deleted_by = None
            self.updated_at = now
            update_fields = [
                'is_deleted', 'deleted_at', 'deleted_by', 'updated_at',
            ]
            if actor:
                self.updated_by = actor
                update_fields.append('updated_by')
            super().save(
                using=database,
                update_fields=update_fields,
            )
            self._cascade_relations(
                'restore', database, actor, cascade_at
            )

        return self

    def hard_delete(self, using=None, keep_parents=False):
        """Hapus permanen; sengaja dipisahkan dari delete() biasa."""
        return super().delete(using=using, keep_parents=keep_parents)


class ApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    CANCELLED = 'cancelled', 'Cancelled'


class ApprovalRequest(AuditModel):
    """Workflow approval generik untuk dokumen dan transaksi operasional."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey('content_type', 'object_id')
    workflow_type = models.CharField(max_length=40)
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    required_role = models.CharField(max_length=30, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approval_requests',
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_decisions',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ('-submitted_at',)
        indexes = [
            models.Index(
                fields=('status', '-submitted_at', 'is_deleted'),
                name='core_approval_queue_idx',
            ),
            models.Index(
                fields=('content_type', 'object_id', 'is_deleted'),
                name='core_approval_object_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=('content_type', 'object_id'),
                condition=models.Q(
                    status=ApprovalStatus.PENDING,
                    is_deleted=False,
                ),
                name='core_unique_pending_approval',
            ),
        ]

    def __str__(self):
        return f'{self.workflow_type}: {self.content_object}'


class ApprovalEvent(AuditModel):
    approval = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name='events',
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(
        max_length=20, choices=ApprovalStatus.choices
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_events',
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'{self.approval} → {self.to_status}'


class ExportJobStatus(models.TextChoices):
    QUEUED = 'queued', 'Queued'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class DataExportJob(AuditModel):
    """Antrian export agar workbook besar tidak memblokir request admin."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    job_type = models.CharField(max_length=40, default='expense')
    status = models.CharField(
        max_length=20,
        choices=ExportJobStatus.choices,
        default=ExportJobStatus.QUEUED,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='data_export_jobs',
    )
    parameters = models.JSONField(default=dict, blank=True)
    result_file = models.FileField(
        upload_to='admin_exports/%Y/%m/',
        null=True,
        blank=True,
    )
    row_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(
                fields=('status', 'created_at'),
                name='core_export_queue_idx',
            ),
        ]

    def __str__(self):
        return f'{self.job_type} export ({self.get_status_display()})'


class Location(models.Model):
    address = gis_models.PointField()
    name = models.TextField()
    latitude  = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name
    

    def save(self, *args, **kwargs):
        """
        Selalu ekstrak (x,y) dari PointField `address` dan simpan
        ke field `longitude` (x) dan `latitude` (y).
        """
        if self.address:
            # Di GeoDjango, point.x = longitude, point.y = latitude
            self.longitude = self.address.x
            self.latitude  = self.address.y
        super().save(*args, **kwargs)

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class IncomeCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class DocumentType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class WorkType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class MaterialCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class ToolCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class UnitType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class FinanceType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class PaymentVia(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
