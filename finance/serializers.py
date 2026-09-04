from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import *
from project.models import ProgressReport
from team.serializers import *
from inventory.serializers import *
from core.serializers import *

class ProjectSimpleSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class BillOfQuantityVersionSerializer(AuditModelSerializer):
    class Meta:
        model = BillOfQuantityVersion
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class SignatureOnBillOfQuantitySerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )
    
    class Meta:
        model = SignatureOnBillOfQuantity
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProgressReportSerializer(AuditModelSerializer):
    class Meta:
        model = ProgressReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class BillOfQuantitySerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    boq_versions = BillOfQuantityVersionSerializer(many=True, read_only=True)
    boq_signatures = SignatureOnBillOfQuantitySerializer(many=True, read_only=True)
    reports_boq = ProgressReportSerializer(many=True, read_only=True)

    class Meta:
        model = BillOfQuantity
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class BillOfQuantitySimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = BillOfQuantity
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class PaymentRequestVersionSerializer(AuditModelSerializer):
    class Meta:
        model = PaymentRequestVersion
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class SignatureOnPaymentRequestSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )

    class Meta:
        model = SignatureOnPaymentRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class PaymentRequestSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    payment_versions = PaymentRequestVersionSerializer(many=True, read_only=True)
    payment_request_signatures = SignatureOnPaymentRequestSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class PaymentRequestSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = PaymentRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class ExpenseLineSerializerMixin:
    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        try:
            instance.save(
                recalculate=self.context.get('recalculate', True)
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, 'message_dict')
                else exc.messages
            )
            raise serializers.ValidationError(detail) from exc
        return instance


class ExpenseDetailSerializer(
    ExpenseLineSerializerMixin, AuditModelSerializer
):
    category = ExpenseCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=ExpenseCategory.objects.all(),
        write_only=True,
    )
    unit = UnitTypeSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        source='unit',
        queryset=UnitType.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ExpenseDetail
        fields = '__all__'
        read_only_fields = (
            'id', 'subtotal', 'discount_amount', 'total',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class ExpenseForMaterialSerializer(
    ExpenseLineSerializerMixin, AuditModelSerializer
):
    material = MaterialSerializer(read_only=True)
    material_id = serializers.PrimaryKeyRelatedField(
        source='material',
        queryset=Material.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    category = ExpenseCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=ExpenseCategory.objects.all(),
        write_only=True,
    )
    unit = UnitTypeSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        source='unit',
        queryset=UnitType.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ExpenseForMaterial
        fields = '__all__'
        read_only_fields = (
            'id', 'subtotal', 'discount_amount', 'total',
            'inventory_applied',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class ExpenseOnProjectSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    expense_detail = ExpenseDetailSerializer(many=True, read_only=True)
    expense_material = ExpenseForMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseOnProject
        fields = '__all__'
        read_only_fields = (
            'id', 'total',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class ExpenseOnProjectSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = ExpenseOnProject
        fields = '__all__'
        read_only_fields = (
            'id', 'total',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class FinanceDataSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = FinanceData
        fields = '__all__'
        read_only_fields = (
            'id', 'balance',
            'is_reconciled', 'reconciled_by', 'reconciled_at',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class PettyCashSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    type = FinanceTypeSerializer(read_only=True)
    type_id = serializers.PrimaryKeyRelatedField(
        source='type',
        queryset=FinanceType.objects.all(),
        write_only=True,
    )
    payment_via = PaymentViaSerializer(read_only=True)
    payment_via_id = serializers.PrimaryKeyRelatedField(
        source='payment_via',
        queryset=PaymentVia.objects.all(),
        write_only=True,
    )

    class Meta:
        model = PettyCash
        fields = '__all__'
        read_only_fields = (
            'id', 'balance',
            'is_reconciled', 'reconciled_by', 'reconciled_at',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )
