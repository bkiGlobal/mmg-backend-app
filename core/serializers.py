from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import *
from team.models import Profile
from django.shortcuts import get_object_or_404


class AuditModelSerializer(serializers.ModelSerializer):
    """Base serializer that keeps audit and soft-delete fields server-managed."""

    audit_read_only_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'is_deleted',
        'deleted_at',
        'deleted_by',
    )

    def get_fields(self):
        fields = super().get_fields()
        for field_name in self.audit_read_only_fields:
            if field_name in fields:
                fields[field_name].read_only = True
        return fields

    @staticmethod
    def _validation_detail(exc):
        if hasattr(exc, 'message_dict'):
            return exc.message_dict
        return exc.messages

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                self._validation_detail(exc)
            ) from exc

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                self._validation_detail(exc)
            ) from exc


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = get_object_or_404(Profile, user=user)
        token['id'] = str(profile.pk)

        return token
    
class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'

class IncomeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IncomeCategory
        fields = '__all__'

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = '__all__'

class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = '__all__'

class MaterialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCategory
        fields = '__all__'

class ToolCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCategory
        fields = '__all__'

class UnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitType
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class FinanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceType
        fields = '__all__'

class PaymentViaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentVia
        fields = '__all__'


class ApprovalEventSerializer(AuditModelSerializer):
    actor_name = serializers.CharField(
        source='actor.get_full_name', read_only=True
    )

    class Meta:
        model = ApprovalEvent
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class ApprovalRequestSerializer(AuditModelSerializer):
    events = ApprovalEventSerializer(many=True, read_only=True)
    object_display = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRequest
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_object_display(self, obj):
        return str(obj.content_object) if obj.content_object else None
