from rest_framework import serializers
from .models import *
from project.models import ProgressReport
from project.serializers import ProjectSimpleSerializer
from team.serializers import SignatureSerializer
from inventory.serializers import MaterialSerializer
from core.serializers import *

class BillOfQuantityVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillOfQuantityVersion
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnBillOfQuantitySerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)
    
    class Meta:
        model = SignatureOnBillOfQuantity
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')


class ProgressReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class BillOfQuantitySerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    boq_versions = BillOfQuantityVersionSerializer(many=True, read_only=True)
    boq_signatures = SignatureOnBillOfQuantitySerializer(many=True, read_only=True)
    reports_boq = ProgressReportSerializer(many=True, read_only=True)

    class Meta:
        model = BillOfQuantity
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class PaymentRequestVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequestVersion
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnPaymentRequestSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)

    class Meta:
        model = SignatureOnPaymentRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class PaymentRequestSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    payment_versions = PaymentRequestVersionSerializer(many=True, read_only=True)
    payment_request_signatures = SignatureOnPaymentRequestSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentRequest
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ExpenseDetailSerializer(serializers.ModelSerializer):
    category = ExpenseCategorySerializer(read_only=True)
    unit_type = UnitTypeSerializer(read_only=True)

    class Meta:
        model = ExpenseDetail
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ExpenseForMaterialSerializer(serializers.ModelSerializer):
    material = MaterialSerializer(read_only=True)
    category = ExpenseCategorySerializer(read_only=True)
    unit_type = UnitTypeSerializer(read_only=True)

    class Meta:
        model = ExpenseForMaterial
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ExpenseOnProjectSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    expense_detail = ExpenseDetailSerializer(many=True, read_only=True)
    expense_material = ExpenseForMaterialSerializer(many=True, read_only=True)

    class Meta:
        model = ExpenseOnProject
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class FinanceDataSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = FinanceData
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class PettyCashSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    type = FinanceTypeSerializer(read_only=True)
    payment_via = PaymentViaSerializer(read_only=True)

    class Meta:
        model = PettyCash
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')