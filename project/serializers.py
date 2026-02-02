from rest_framework import serializers
from .models import *
from core.serializers import *
from team.serializers import *
from finance.serializers import *

class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnDocumentSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)

    class Meta:
        model = SignatureOnDocument
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DocumentSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    document_type = DocumentTypeSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    document_signatures = SignatureOnDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DocumentSimpleSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    document_type = DocumentTypeSerializer(read_only=True)

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DrawingVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrawingVersion
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnDrawingSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)
    class Meta:
        model = SignatureOnDrawing
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DrawingSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    drawing_type = DocumentTypeSerializer(read_only=True)
    drawing_versions = DrawingVersionSerializer(many=True, read_only=True)
    drawing_signatures = SignatureOnDrawingSerializer(many=True, read_only=True)

    class Meta:
        model = Drawing
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DrawingSimpleSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    drawing_type = DocumentTypeSerializer(read_only=True)

    class Meta:
        model = Drawing
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DefectDetailSerializer(serializers.ModelSerializer):
    initial_checklist_approval = InitialSerializer(read_only=True)
    final_checklist_approval = InitialSerializer(read_only=True)

    class Meta:
        model = DefectDetail
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnDeflectSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)

    class Meta:
        model = SignatureOnDeflect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DefectSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    defect_detail = DefectDetailSerializer(many=True, read_only=True)
    defect_signature = SignatureOnDeflectSerializer(many=True, read_only=True)

    class Meta:
        model = Defect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DefectSimpleSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = Defect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ErrorLogDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorLogDetail
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnErrorLogSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)

    class Meta:
        model = SignatureOnErrorLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ErrorLogSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    work_type = WorkTypeSerializer(read_only=True)
    error_detail = ErrorLogDetailSerializer(many=True, read_only=True)
    error_log_signature = SignatureOnErrorLogSerializer(many=True, read_only=True)

    class Meta:
        model = ErrorLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnScheduleSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)

    class Meta:
        model = SignatureOnSchedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ScheduleSerializer(serializers.ModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)
    schedule_signature = SignatureOnScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ScheduleSimpleSerializer(serializers.ModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProgressReportSerializer(serializers.ModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)

    class Meta:
        model = ProgressReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnWorkMethodSerializer(serializers.ModelSerializer):
    signature = SignatureSerializer(read_only=True)
    
    class Meta:
        model = SignatureOnWorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class WorkMethodSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    work_method_signature = SignatureOnWorkMethodSerializer(many=True, read_only=True)

    class Meta:
        model = WorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class WorkMethodSimpleSerializer(serializers.ModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = WorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProjectSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    client = ProfileSimpleSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    project_documents = DocumentSerializer(many=True, read_only=True)
    project_drawings = DrawingSerializer(many=True, read_only=True)
    project_defect = DefectSerializer(many=True, read_only=True)
    error_on_project = ErrorLogSerializer(many=True, read_only=True)
    work_method_project = WorkMethodSerializer(many=True, read_only=True)
    project_boqs = BillOfQuantitySerializer(many=True, read_only=True)
    project_payment_requests = PaymentRequestSerializer(many=True, read_only=True)
    project_expense = ExpenseOnProjectSerializer(many=True, read_only=True)
    project_finance_data = FinanceDataSerializer(many=True, read_only=True)
    project_petty_cash = PettyCashSerializer(many=True, read_only=True)
    project_material = MaterialOnProjectSerializer(many=True, read_only=True)
    project_tools = ToolOnProjectSerializer(many=True, read_only=True)
    project_subcon = SubContractorOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')