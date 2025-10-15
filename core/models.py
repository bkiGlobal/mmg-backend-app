from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django_currentuser.middleware import get_current_authenticated_user

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

    def save(self, *args, **kwargs):
        user = get_current_authenticated_user()
        if self.created_by:
            self.updated_by = user
        else:
            self.created_by = user
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """
        Soft delete: tandai tanpa hapus fisik.
        """
        user = get_current_authenticated_user()
        self.is_deleted  = True
        self.deleted_at  = timezone.now()
        if user:
            self.deleted_by = user
        self.save()

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