from datetime import timezone
from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as gis_models

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

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete: tandai tanpa hapus fisik."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        # deleted_by di-set di view/servis sebelum memanggil delete()
        self.save()

class Location(models.Model):
    address = gis_models.PointField()
    name = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()


    def __str__(self):
        return self.name