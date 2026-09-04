from rest_framework import serializers
from .models import *
from core.serializers import *
from team.serializers import ProfileSimpleSerializer
from core.permissions import accessible_project_ids
from rest_framework.exceptions import PermissionDenied


def validate_inventory_project(serializer, attrs):
    request = serializer.context.get('request')
    if request is None:
        return
    project = attrs.get('project')
    if project is None and serializer.instance is not None:
        project = serializer.instance.project
    if project is None:
        return
    allowed_ids = accessible_project_ids(
        request.user, global_roles={'logistic'}
    )
    if allowed_ids is not None and project.pk not in set(allowed_ids):
        raise PermissionDenied(
            'Anda tidak dapat menulis inventory pada proyek ini.'
        )

class ProjectSimpleSerializer(AuditModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class MaterialOnProjectSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    material_id = serializers.PrimaryKeyRelatedField(
        source='material',
        queryset=Material.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    approved_by = ProfileSimpleSerializer(read_only=True)
    approved_by_id = serializers.PrimaryKeyRelatedField(
        source='approved_by',
        queryset=Profile.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MaterialOnProject
        fields = '__all__'
        read_only_fields = (
            'id', 'approved_by', 'approved_date',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

    def validate(self, attrs):
        validate_inventory_project(self, attrs)
        attrs.pop('approved_by', None)
        return super().validate(attrs)

class MaterialSerializer(AuditModelSerializer):
    category = MaterialCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=MaterialCategory.objects.all(),
        write_only=True,
    )
    brand = BrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        source='brand',
        queryset=Brand.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    unit = UnitTypeSerializer(read_only=True)
    unit_id = serializers.PrimaryKeyRelatedField(
        source='unit',
        queryset=UnitType.objects.all(),
        write_only=True,
    )
    material_project = MaterialOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

class MaterialSimpleSerializer(AuditModelSerializer):
    category = MaterialCategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    unit = UnitTypeSerializer(read_only=True)

    class Meta:
        model = Material
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')

class ToolOnProjectSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    tool_id = serializers.PrimaryKeyRelatedField(
        source='tool',
        queryset=Tool.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ToolOnProject
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )

    def validate(self, attrs):
        validate_inventory_project(self, attrs)
        return super().validate(attrs)

class ToolSerializer(AuditModelSerializer):
    category = ToolCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source='category',
        queryset=ToolCategory.objects.all(),
        write_only=True,
    )
    tools_project = ToolOnProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Tool
        fields = '__all__'
        read_only_fields = (
            'id', 'available',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )
    
class ToolSimpleSerializer(AuditModelSerializer):
    category = ToolCategorySerializer(read_only=True)

    class Meta:
        model = Tool
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'created_by', 'updated_at', 'updated_by')


class StockMovementSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    material = MaterialSimpleSerializer(read_only=True)

    class Meta:
        model = StockMovement
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class PurchaseRequestSerializer(AuditModelSerializer):
    project = ProjectSimpleSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True,
    )
    material = MaterialSimpleSerializer(read_only=True)
    material_id = serializers.PrimaryKeyRelatedField(
        source='material',
        queryset=Material.objects.all(),
        write_only=True,
    )
    requested_by = ProfileSimpleSerializer(read_only=True)
    approved_by = ProfileSimpleSerializer(read_only=True)

    class Meta:
        model = PurchaseRequest
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'requested_by', 'approved_by',
            'approved_at', 'ordered_at', 'received_at',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )


class ToolMaintenanceSerializer(AuditModelSerializer):
    tool = ToolSimpleSerializer(read_only=True)
    tool_id = serializers.PrimaryKeyRelatedField(
        source='tool',
        queryset=Tool.objects.all(),
        write_only=True,
    )

    class Meta:
        model = ToolMaintenance
        fields = '__all__'
        read_only_fields = (
            'id', 'status', 'completed_date',
            'created_at', 'created_by', 'updated_at', 'updated_by',
            'is_deleted', 'deleted_at', 'deleted_by',
        )
