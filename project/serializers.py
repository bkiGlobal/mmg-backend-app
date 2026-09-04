from rest_framework import serializers
from .models import *
from core.serializers import *
from team.serializers import *
from finance.serializers import *

class DocumentVersionSerializer(AuditModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class SignatureOnDocumentSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )

    class Meta:
        model = SignatureOnDocument
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DocumentSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    document_type = DocumentTypeSerializer(read_only=True)
    document_type_id = serializers.PrimaryKeyRelatedField(
        source='document_type',
        queryset=DocumentType.objects.all(),
        write_only=True,
    )
    versions = DocumentVersionSerializer(many=True, read_only=True)
    document_signatures = SignatureOnDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class DocumentSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    document_type = DocumentTypeSerializer(read_only=True)

    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class DrawingVersionSerializer(AuditModelSerializer):
    class Meta:
        model = DrawingVersion
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class SignatureOnDrawingSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )
    class Meta:
        model = SignatureOnDrawing
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DrawingSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    drawing_type = DocumentTypeSerializer(read_only=True)
    drawing_type_id = serializers.PrimaryKeyRelatedField(
        source='drawing_type',
        queryset=DocumentType.objects.all(),
        write_only=True,
    )
    drawing_versions = DrawingVersionSerializer(many=True, read_only=True)
    drawing_signatures = SignatureOnDrawingSerializer(many=True, read_only=True)

    class Meta:
        model = Drawing
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class DrawingSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    drawing_type = DocumentTypeSerializer(read_only=True)

    class Meta:
        model = Drawing
        fields = '__all__'
        read_only_fields = (
            'id', 'status',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )

class DefectDetailSerializer(AuditModelSerializer):
    initial_checklist_approval = InitialSerializer(read_only=True)
    initial_checklist_approval_id = serializers.PrimaryKeyRelatedField(
        source='initial_checklist_approval',
        queryset=Initial.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    final_checklist_approval = InitialSerializer(read_only=True)
    final_checklist_approval_id = serializers.PrimaryKeyRelatedField(
        source='final_checklist_approval',
        queryset=Initial.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = DefectDetail
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnDeflectSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
    )

    class Meta:
        model = SignatureOnDeflect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DefectSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    defect_detail = DefectDetailSerializer(many=True, read_only=True)
    defect_signature = SignatureOnDeflectSerializer(many=True, read_only=True)

    class Meta:
        model = Defect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class DefectSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = Defect
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ErrorLogDetailSerializer(AuditModelSerializer):
    class Meta:
        model = ErrorLogDetail
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnErrorLogSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SignatureOnErrorLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ErrorLogSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    work_type = WorkTypeSerializer(read_only=True)
    work_type_id = serializers.PrimaryKeyRelatedField(
        source='work_type',
        queryset=WorkType.objects.all(),
        write_only=True,
    )
    error_detail = ErrorLogDetailSerializer(many=True, read_only=True)
    error_log_signature = SignatureOnErrorLogSerializer(many=True, read_only=True)

    class Meta:
        model = ErrorLog
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnScheduleSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SignatureOnSchedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ScheduleSerializer(AuditModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)
    boq_item_id = serializers.PrimaryKeyRelatedField(
        source='boq_item',
        queryset=BillOfQuantity.objects.all(),
        write_only=True,
    )
    schedule_signature = SignatureOnScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ScheduleSimpleSerializer(AuditModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)

    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProgressReportSerializer(AuditModelSerializer):
    boq_item = BillOfQuantitySimpleSerializer(read_only=True)
    boq_item_id = serializers.PrimaryKeyRelatedField(
        source='boq_item',
        queryset=BillOfQuantity.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ProgressReport
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class SignatureOnWorkMethodSerializer(AuditModelSerializer):
    signature = SignatureSerializer(read_only=True)
    signature_id = serializers.PrimaryKeyRelatedField(
        source='signature',
        queryset=Signature.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    class Meta:
        model = SignatureOnWorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class WorkMethodSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    work_method_signature = SignatureOnWorkMethodSerializer(many=True, read_only=True)

    class Meta:
        model = WorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class WorkMethodSimpleSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)

    class Meta:
        model = WorkMethod
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ProjectSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        source='location',
        queryset=Location.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    client = ProfileSimpleSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        source='client',
        queryset=Profile.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    team = TeamSerializer(read_only=True)
    team_id = serializers.PrimaryKeyRelatedField(
        source='team',
        queryset=Team.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
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
        read_only_fields = (
            'id', 'progress',
            'created_at', 'created_by', 'updated_at', 'updated_by',
        )
